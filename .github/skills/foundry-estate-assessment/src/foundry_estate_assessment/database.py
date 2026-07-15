"""SQLite state store.

The assessment database is the durable source of truth for progress and
evidence. It lives under the caller-chosen output directory (never inside the
installed skill). Writes use short transactions so a Ctrl+C leaves a
consistent, resumable state.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessment_runs (
    assessment_id TEXT PRIMARY KEY,
    scope_kind TEXT NOT NULL,
    scope_values TEXT NOT NULL,
    tenant_id TEXT,
    identity TEXT,
    identity_type TEXT,
    cli_version TEXT,
    scanner_version TEXT NOT NULL,
    standard_id TEXT,
    standard_version TEXT,
    started_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    concurrency INTEGER,
    output_dir TEXT,
    no_raw_evidence INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inventory_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    scope_kind TEXT NOT NULL,
    scope_values TEXT NOT NULL,
    subscriptions_accessible INTEGER DEFAULT 0,
    subscriptions_inventoried INTEGER DEFAULT 0,
    candidate_foundries INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subscriptions (
    snapshot_id TEXT NOT NULL,
    subscription_id TEXT NOT NULL,
    name TEXT,
    state TEXT,
    accessible INTEGER DEFAULT 1,
    reason TEXT,
    PRIMARY KEY (snapshot_id, subscription_id)
);

CREATE TABLE IF NOT EXISTS resources (
    snapshot_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    subscription_id TEXT,
    resource_group TEXT,
    name TEXT,
    resource_type TEXT,
    kind TEXT,
    sku TEXT,
    location TEXT,
    tags TEXT,
    classification TEXT,
    properties TEXT,
    source_query TEXT,
    discovered_at TEXT,
    PRIMARY KEY (snapshot_id, resource_id)
);

CREATE TABLE IF NOT EXISTS relationships (
    snapshot_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    evidence_type TEXT,
    confidence TEXT,
    collected_at TEXT,
    PRIMARY KEY (snapshot_id, source_id, target_id, relationship_type)
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    collector TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt_count INTEGER DEFAULT 0,
    created_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    lease_expiry TEXT,
    next_retry TEXT,
    last_error_class TEXT,
    last_error TEXT,
    collector_version TEXT
);

CREATE TABLE IF NOT EXISTS evidence (
    snapshot_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    collector TEXT NOT NULL,
    fact TEXT NOT NULL,
    collection_status TEXT NOT NULL,
    raw_path TEXT,
    raw_sha256 TEXT,
    api_version TEXT,
    collected_at TEXT,
    collector_version TEXT,
    sanitized INTEGER DEFAULT 1,
    PRIMARY KEY (snapshot_id, resource_id, collector)
);

CREATE TABLE IF NOT EXISTS metrics (
    snapshot_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    unit TEXT,
    metric_timestamp TEXT,
    aggregation_period TEXT,
    PRIMARY KEY (snapshot_id, resource_id, metric)
);

CREATE TABLE IF NOT EXISTS findings (
    assessment_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    rule_version TEXT,
    result TEXT NOT NULL,
    effective_result TEXT,
    severity TEXT,
    expected TEXT,
    actual TEXT,
    explanation TEXT,
    recommended_investigation TEXT,
    collection_status TEXT,
    foundry_resource_id TEXT,
    project_resource_id TEXT,
    evidence_ref TEXT,
    exception_id TEXT,
    evaluated_at TEXT,
    PRIMARY KEY (assessment_id, snapshot_id, resource_id, rule_id)
);

CREATE TABLE IF NOT EXISTS effort_estimates (
    assessment_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL,
    foundry_resource_id TEXT NOT NULL,
    band TEXT NOT NULL,
    confidence TEXT,
    drivers TEXT,
    data_gb REAL,
    unknown_dependencies TEXT,
    PRIMARY KEY (assessment_id, snapshot_id, foundry_resource_id)
);
"""


def _dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


class Database:
    """Thin DAO over SQLite with deterministic ordering."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # The scheduler runs collectors on a thread pool. A single connection
        # shared across threads is safe as long as every access is serialized;
        # ``check_same_thread=False`` plus an explicit lock provides that.
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._lock = threading.RLock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self.transaction() as conn:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO schema_meta (key, value) VALUES ('schema_version', ?)",
                (str(SCHEMA_VERSION),),
            )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def _fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        # Reads must execute AND fetch under the lock: the connection is shared
        # across scheduler worker threads, so an interleaved write between
        # ``execute`` and ``fetch`` could corrupt or invalidate results.
        with self._lock:
            return list(self._conn.execute(sql, params).fetchall())

    def _fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def close(self) -> None:
        self._conn.close()

    # -- assessment runs --------------------------------------------------
    def upsert_run(self, run: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO assessment_runs (
                    assessment_id, scope_kind, scope_values, tenant_id, identity,
                    identity_type, cli_version, scanner_version, standard_id,
                    standard_version, started_at, updated_at, concurrency, output_dir,
                    no_raw_evidence)
                VALUES (:assessment_id, :scope_kind, :scope_values, :tenant_id, :identity,
                    :identity_type, :cli_version, :scanner_version, :standard_id,
                    :standard_version, :started_at, :updated_at, :concurrency, :output_dir,
                    :no_raw_evidence)
                ON CONFLICT(assessment_id) DO UPDATE SET
                    tenant_id=excluded.tenant_id, identity=excluded.identity,
                    identity_type=excluded.identity_type, cli_version=excluded.cli_version,
                    standard_id=excluded.standard_id, standard_version=excluded.standard_version,
                    updated_at=excluded.updated_at, concurrency=excluded.concurrency,
                    no_raw_evidence=excluded.no_raw_evidence
                """,
                run,
            )

    def latest_run(self) -> Optional[sqlite3.Row]:
        return self._fetchone(
            "SELECT * FROM assessment_runs ORDER BY started_at DESC LIMIT 1"
        )

    # -- snapshots --------------------------------------------------------
    def create_snapshot(self, snapshot: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO inventory_snapshots (
                    snapshot_id, assessment_id, created_at, scope_kind, scope_values,
                    subscriptions_accessible, subscriptions_inventoried, candidate_foundries)
                VALUES (:snapshot_id, :assessment_id, :created_at, :scope_kind, :scope_values,
                    :subscriptions_accessible, :subscriptions_inventoried, :candidate_foundries)
                """,
                snapshot,
            )

    def update_snapshot_counts(self, snapshot_id: str, **counts: int) -> None:
        if not counts:
            return
        assignments = ", ".join(f"{key} = :{key}" for key in counts)
        with self.transaction() as conn:
            conn.execute(
                f"UPDATE inventory_snapshots SET {assignments} WHERE snapshot_id = :snapshot_id",
                {**counts, "snapshot_id": snapshot_id},
            )

    def latest_snapshot(self, assessment_id: str) -> Optional[sqlite3.Row]:
        return self._fetchone(
            "SELECT * FROM inventory_snapshots WHERE assessment_id = ? ORDER BY created_at DESC LIMIT 1",
            (assessment_id,),
        )

    def list_snapshots(self, assessment_id: str) -> list[sqlite3.Row]:
        return self._fetchall(
            "SELECT * FROM inventory_snapshots WHERE assessment_id = ? ORDER BY created_at ASC",
            (assessment_id,),
        )

    # -- subscriptions ----------------------------------------------------
    def upsert_subscription(self, snapshot_id: str, sub: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO subscriptions
                    (snapshot_id, subscription_id, name, state, accessible, reason)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    sub["subscription_id"],
                    sub.get("name"),
                    sub.get("state"),
                    1 if sub.get("accessible", True) else 0,
                    sub.get("reason"),
                ),
            )

    def list_subscriptions(self, snapshot_id: str) -> list[sqlite3.Row]:
        return self._fetchall(
            "SELECT * FROM subscriptions WHERE snapshot_id = ? ORDER BY subscription_id",
            (snapshot_id,),
        )

    # -- resources --------------------------------------------------------
    def upsert_resource(self, snapshot_id: str, record: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO resources (
                    snapshot_id, resource_id, subscription_id, resource_group, name,
                    resource_type, kind, sku, location, tags, classification, properties,
                    source_query, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    record["resource_id"],
                    record.get("subscription_id"),
                    record.get("resource_group"),
                    record.get("name"),
                    record.get("resource_type"),
                    record.get("kind"),
                    record.get("sku"),
                    record.get("location"),
                    _dumps(record.get("tags", {})),
                    record.get("classification"),
                    _dumps(record.get("properties", {})),
                    record.get("source_query"),
                    record.get("discovered_at"),
                ),
            )

    def get_resource(self, snapshot_id: str, resource_id: str) -> Optional[sqlite3.Row]:
        return self._fetchone(
            "SELECT * FROM resources WHERE snapshot_id = ? AND resource_id = ?",
            (snapshot_id, resource_id),
        )

    def list_resources(self, snapshot_id: str, classifications: Optional[list[str]] = None) -> list[sqlite3.Row]:
        if classifications:
            placeholders = ",".join("?" for _ in classifications)
            return self._fetchall(
                f"SELECT * FROM resources WHERE snapshot_id = ? AND classification IN ({placeholders}) ORDER BY resource_id",
                (snapshot_id, *classifications),
            )
        return self._fetchall(
            "SELECT * FROM resources WHERE snapshot_id = ? ORDER BY resource_id",
            (snapshot_id,),
        )

    # -- relationships ----------------------------------------------------
    def upsert_relationship(self, snapshot_id: str, rel: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO relationships
                    (snapshot_id, source_id, target_id, relationship_type, evidence_type,
                     confidence, collected_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    rel["source_id"],
                    rel["target_id"],
                    rel["relationship_type"],
                    rel.get("evidence_type"),
                    rel.get("confidence"),
                    rel.get("collected_at"),
                ),
            )

    def list_relationships(self, snapshot_id: str) -> list[sqlite3.Row]:
        return self._fetchall(
            "SELECT * FROM relationships WHERE snapshot_id = ? ORDER BY source_id, target_id, relationship_type",
            (snapshot_id,),
        )

    def relationships_from(self, snapshot_id: str, source_id: str) -> list[sqlite3.Row]:
        return self._fetchall(
            "SELECT * FROM relationships WHERE snapshot_id = ? AND source_id = ? ORDER BY target_id, relationship_type",
            (snapshot_id, source_id),
        )

    def relationships_to(self, snapshot_id: str, target_id: str) -> list[sqlite3.Row]:
        return self._fetchall(
            "SELECT * FROM relationships WHERE snapshot_id = ? AND target_id = ? ORDER BY source_id, relationship_type",
            (snapshot_id, target_id),
        )

    # -- tasks ------------------------------------------------------------
    def upsert_task(self, task: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                    task_id, assessment_id, snapshot_id, resource_id, collector, status,
                    attempt_count, created_at, started_at, completed_at, lease_expiry,
                    next_retry, last_error_class, last_error, collector_version)
                VALUES (:task_id, :assessment_id, :snapshot_id, :resource_id, :collector, :status,
                    :attempt_count, :created_at, :started_at, :completed_at, :lease_expiry,
                    :next_retry, :last_error_class, :last_error, :collector_version)
                ON CONFLICT(task_id) DO UPDATE SET
                    status=excluded.status, attempt_count=excluded.attempt_count,
                    started_at=excluded.started_at, completed_at=excluded.completed_at,
                    lease_expiry=excluded.lease_expiry, next_retry=excluded.next_retry,
                    last_error_class=excluded.last_error_class, last_error=excluded.last_error,
                    collector_version=excluded.collector_version
                """,
                task,
            )

    def get_task(self, task_id: str) -> Optional[sqlite3.Row]:
        return self._fetchone("SELECT * FROM tasks WHERE task_id = ?", (task_id,))

    def list_tasks(self, assessment_id: str, snapshot_id: str) -> list[sqlite3.Row]:
        return self._fetchall(
            "SELECT * FROM tasks WHERE assessment_id = ? AND snapshot_id = ? ORDER BY task_id",
            (assessment_id, snapshot_id),
        )

    def set_task_status(self, task_id: str, **fields: Any) -> None:
        if not fields:
            return
        assignments = ", ".join(f"{key} = :{key}" for key in fields)
        with self.transaction() as conn:
            conn.execute(
                f"UPDATE tasks SET {assignments} WHERE task_id = :task_id",
                {**fields, "task_id": task_id},
            )

    # -- evidence & metrics ----------------------------------------------
    def upsert_evidence(self, snapshot_id: str, resource_id: str, collector: str, record: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO evidence (
                    snapshot_id, resource_id, collector, fact, collection_status, raw_path,
                    raw_sha256, api_version, collected_at, collector_version, sanitized)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    resource_id,
                    collector,
                    _dumps(record.get("fact", {})),
                    record.get("collection_status", "UNKNOWN"),
                    record.get("raw_path"),
                    record.get("raw_sha256"),
                    record.get("api_version"),
                    record.get("collected_at"),
                    record.get("collector_version"),
                    1 if record.get("sanitized", True) else 0,
                ),
            )

    def get_evidence(self, snapshot_id: str, resource_id: str, collector: str) -> Optional[dict[str, Any]]:
        row = self._fetchone(
            "SELECT * FROM evidence WHERE snapshot_id = ? AND resource_id = ? AND collector = ?",
            (snapshot_id, resource_id, collector),
        )
        if row is None:
            return None
        data = dict(row)
        data["fact"] = json.loads(data["fact"]) if data["fact"] else {}
        return data

    def list_evidence(self, snapshot_id: str) -> list[dict[str, Any]]:
        out = []
        for row in self._fetchall(
            "SELECT * FROM evidence WHERE snapshot_id = ? ORDER BY resource_id, collector",
            (snapshot_id,),
        ):
            data = dict(row)
            data["fact"] = json.loads(data["fact"]) if data["fact"] else {}
            out.append(data)
        return out

    def upsert_metric(self, snapshot_id: str, resource_id: str, metric: str, value: Optional[float], unit: str, timestamp: Optional[str], period: Optional[str]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO metrics
                    (snapshot_id, resource_id, metric, value, unit, metric_timestamp, aggregation_period)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (snapshot_id, resource_id, metric, value, unit, timestamp, period),
            )

    # -- findings & effort ------------------------------------------------
    def clear_findings(self, assessment_id: str, snapshot_id: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "DELETE FROM findings WHERE assessment_id = ? AND snapshot_id = ?",
                (assessment_id, snapshot_id),
            )

    def insert_finding(self, assessment_id: str, snapshot_id: str, finding: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO findings (
                    assessment_id, snapshot_id, resource_id, rule_id, rule_version, result,
                    effective_result, severity, expected, actual, explanation,
                    recommended_investigation, collection_status, foundry_resource_id,
                    project_resource_id, evidence_ref, exception_id, evaluated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    snapshot_id,
                    finding["resource_id"],
                    finding["rule_id"],
                    finding.get("rule_version"),
                    finding["result"],
                    finding.get("effective_result"),
                    finding.get("severity"),
                    _dumps(finding.get("expected")),
                    _dumps(finding.get("actual")),
                    finding.get("explanation"),
                    finding.get("recommended_investigation"),
                    finding.get("collection_status"),
                    finding.get("foundry_resource_id"),
                    finding.get("project_resource_id"),
                    finding.get("evidence_ref"),
                    finding.get("exception_id"),
                    finding.get("evaluated_at"),
                ),
            )

    def list_findings(self, assessment_id: str, snapshot_id: str) -> list[sqlite3.Row]:
        return self._fetchall(
            "SELECT * FROM findings WHERE assessment_id = ? AND snapshot_id = ? ORDER BY resource_id, rule_id",
            (assessment_id, snapshot_id),
        )

    def clear_effort(self, assessment_id: str, snapshot_id: str) -> None:
        with self.transaction() as conn:
            conn.execute(
                "DELETE FROM effort_estimates WHERE assessment_id = ? AND snapshot_id = ?",
                (assessment_id, snapshot_id),
            )

    def insert_effort(self, assessment_id: str, snapshot_id: str, estimate: dict[str, Any]) -> None:
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO effort_estimates
                    (assessment_id, snapshot_id, foundry_resource_id, band, confidence,
                     drivers, data_gb, unknown_dependencies)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    snapshot_id,
                    estimate["foundry_resource_id"],
                    estimate["band"],
                    estimate.get("confidence"),
                    _dumps(estimate.get("drivers", [])),
                    estimate.get("data_gb", 0.0),
                    _dumps(estimate.get("unknown_dependencies", [])),
                ),
            )

    def list_effort(self, assessment_id: str, snapshot_id: str) -> list[sqlite3.Row]:
        return self._fetchall(
            "SELECT * FROM effort_estimates WHERE assessment_id = ? AND snapshot_id = ? ORDER BY foundry_resource_id",
            (assessment_id, snapshot_id),
        )

    def list_metrics(self, snapshot_id: str) -> list[sqlite3.Row]:
        return self._fetchall(
            "SELECT * FROM metrics WHERE snapshot_id = ? ORDER BY resource_id, metric",
            (snapshot_id,),
        )
