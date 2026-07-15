"""Collectors: deterministic evidence gatherers, one concern each.

Every collector receives a :class:`CollectorContext`, fetches a bounded set of
Azure facts through :class:`~foundry_estate_assessment.azure_cli.AzureClient`,
persists sanitized raw evidence, writes normalized facts / relationships /
metrics to the database, and returns a
:class:`~foundry_estate_assessment.scheduler.TaskOutcome`.

Collectors never read secret values and never raise on empty data: missing
evidence becomes ``UNKNOWN`` collection status, not a crash.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ..azure_cli import AzureClient
from ..database import Database
from ..evidence import EvidenceStore, utcnow
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome, TaskStatus


@dataclass
class CollectorContext:
    db: Database
    client: AzureClient
    snapshot_id: str
    evidence: EvidenceStore

    def store_fact(
        self,
        resource_id: str,
        collector: str,
        fact: dict[str, Any],
        raw: Any,
        api_version: str,
        status: EvidenceStatus = EvidenceStatus.SUCCEEDED,
    ) -> None:
        provenance = self.evidence.persist_raw(resource_id, collector, raw, api_version)
        self.db.upsert_evidence(
            self.snapshot_id,
            resource_id,
            collector,
            {
                "fact": fact,
                "collection_status": status.value,
                "raw_path": provenance["raw_path"],
                "raw_sha256": provenance["raw_sha256"],
                "api_version": api_version,
                "collected_at": provenance["collected_at"],
                "collector_version": provenance["collector_version"],
                "sanitized": True,
            },
        )

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        evidence_type: str,
        confidence: str = "PROVEN",
    ) -> None:
        self.db.upsert_relationship(
            self.snapshot_id,
            {
                "source_id": source_id,
                "target_id": target_id,
                "relationship_type": relationship_type,
                "evidence_type": evidence_type,
                "confidence": confidence,
                "collected_at": utcnow(),
            },
        )

    def add_metric(
        self,
        resource_id: str,
        metric: str,
        value: Optional[float],
        unit: str = "count",
        timestamp: Optional[str] = None,
        period: Optional[str] = None,
    ) -> None:
        self.db.upsert_metric(
            self.snapshot_id, resource_id, metric, value, unit, timestamp or utcnow(), period
        )

    def register_resource(self, record: dict[str, Any]) -> None:
        """Register a peripheral resource discovered during collection."""
        if self.db.get_resource(self.snapshot_id, record["resource_id"]) is not None:
            return
        record.setdefault("discovered_at", utcnow())
        record.setdefault("source_query", "relationship-discovery")
        self.db.upsert_resource(self.snapshot_id, record)


def ok() -> TaskOutcome:
    return TaskOutcome(status=TaskStatus.SUCCEEDED)


def partial(reason: str = "") -> TaskOutcome:
    return TaskOutcome(status=TaskStatus.PARTIAL, error=reason or None)


def _first_sku_name(sku: Any) -> Optional[str]:
    if isinstance(sku, dict):
        return sku.get("name")
    if isinstance(sku, str):
        return sku
    return None


def parse_resource_group(resource_id: str) -> Optional[str]:
    parts = resource_id.split("/")
    for index, token in enumerate(parts):
        if token.lower() == "resourcegroups" and index + 1 < len(parts):
            return parts[index + 1]
    return None


def parse_subscription(resource_id: str) -> Optional[str]:
    parts = resource_id.split("/")
    for index, token in enumerate(parts):
        if token.lower() == "subscriptions" and index + 1 < len(parts):
            return parts[index + 1]
    return None
