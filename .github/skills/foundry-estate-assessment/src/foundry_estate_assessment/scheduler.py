"""Task scheduler: bounded-concurrency, resumable, checkpointed execution.

The scheduler owns task lifecycle. It is deliberately phase-agnostic: callers
supply a list of :class:`TaskSpec` and a mapping of collector name to an
executor callable. The scheduler creates/loads task rows, resets expired
leases, skips already-succeeded work, applies retry timing and backoff, runs a
small thread pool, and checkpoints after every task.

Ctrl+C stops scheduling new work, lets in-flight database writes finish,
releases leases, and prints the resume command.
"""

from __future__ import annotations

import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from .azure_cli import (
    AuthenticationError,
    AuthorizationError,
    MalformedResponseError,
    NetworkError,
    ThrottlingError,
    UnsupportedApiError,
)
from .database import Database
from .evidence import utcnow
from .models import TaskStatus

LEASE_SECONDS = 300
MAX_ATTEMPTS = 5


@dataclass
class TaskSpec:
    resource_id: str
    collector: str

    @property
    def task_id(self) -> str:
        return f"{self.collector}::{self.resource_id}"


@dataclass
class TaskOutcome:
    status: TaskStatus
    error_class: Optional[str] = None
    error: Optional[str] = None
    retry_after: Optional[float] = None


#: A collector executor takes a resource_id and returns a TaskOutcome.
Executor = Callable[[str], TaskOutcome]


@dataclass
class SchedulerStats:
    succeeded: int = 0
    partial: int = 0
    failed: int = 0
    blocked: int = 0
    skipped: int = 0
    interrupted: bool = False
    per_collector: dict[str, dict[str, int]] = field(default_factory=dict)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def classify_exception(exc: Exception) -> tuple[TaskStatus, str, Optional[float]]:
    """Map a collector exception to a task status and retry hint."""
    if isinstance(exc, AuthorizationError):
        return TaskStatus.BLOCKED_PERMISSION, "AuthorizationError", None
    if isinstance(exc, AuthenticationError):
        return TaskStatus.FAILED, "AuthenticationError", None
    if isinstance(exc, NetworkError):
        return TaskStatus.BLOCKED_NETWORK, "NetworkError", None
    if isinstance(exc, ThrottlingError):
        return TaskStatus.RETRYABLE_ERROR, "ThrottlingError", exc.retry_after
    if isinstance(exc, UnsupportedApiError):
        return TaskStatus.UNSUPPORTED, "UnsupportedApiError", None
    if isinstance(exc, MalformedResponseError):
        return TaskStatus.RETRYABLE_ERROR, "MalformedResponseError", None
    if isinstance(exc, OSError):
        # Local IO/OS failures (e.g. a path exceeding MAX_PATH, permission
        # denied) are deterministic, not transient: retrying never helps and
        # would mask the real cause. Fail hard so the error surfaces.
        return TaskStatus.FAILED, exc.__class__.__name__, None
    return TaskStatus.RETRYABLE_ERROR, exc.__class__.__name__, None


class Scheduler:
    def __init__(
        self,
        db: Database,
        assessment_id: str,
        snapshot_id: str,
        concurrency: int = 4,
        retry_blocked: bool = False,
        refresh: bool = False,
        max_attempts: int = MAX_ATTEMPTS,
    ) -> None:
        self.db = db
        self.assessment_id = assessment_id
        self.snapshot_id = snapshot_id
        self.concurrency = max(1, concurrency)
        self.retry_blocked = retry_blocked
        self.refresh = refresh
        self.max_attempts = max_attempts
        self._db_lock = threading.Lock()
        self._stop = threading.Event()

    def request_stop(self) -> None:
        self._stop.set()

    # -- task materialization --------------------------------------------
    def ensure_tasks(self, specs: list[TaskSpec]) -> None:
        """Create task rows that do not yet exist; never resets progress."""
        now = utcnow()
        for spec in specs:
            if self.db.get_task(spec.task_id) is not None:
                continue
            self.db.upsert_task(
                {
                    "task_id": spec.task_id,
                    "assessment_id": self.assessment_id,
                    "snapshot_id": self.snapshot_id,
                    "resource_id": spec.resource_id,
                    "collector": spec.collector,
                    "status": TaskStatus.PENDING.value,
                    "attempt_count": 0,
                    "created_at": now,
                    "started_at": None,
                    "completed_at": None,
                    "lease_expiry": None,
                    "next_retry": None,
                    "last_error_class": None,
                    "last_error": None,
                    "collector_version": None,
                }
            )

    def reclaim_expired_leases(self) -> None:
        """Reset RUNNING tasks whose lease has expired back to PENDING."""
        now = _now()
        for row in self.db.list_tasks(self.assessment_id, self.snapshot_id):
            if row["status"] != TaskStatus.RUNNING.value:
                continue
            expiry = _parse(row["lease_expiry"])
            if expiry is None or expiry <= now:
                self.db.set_task_status(
                    row["task_id"],
                    status=TaskStatus.PENDING.value,
                    lease_expiry=None,
                )

    def _is_runnable(self, row) -> bool:
        status = row["status"]
        if status in (TaskStatus.SUCCEEDED.value,):
            return self.refresh
        if status == TaskStatus.PARTIAL.value:
            return True
        if status in (TaskStatus.BLOCKED_PERMISSION.value, TaskStatus.BLOCKED_NETWORK.value):
            return self.retry_blocked
        if status == TaskStatus.UNSUPPORTED.value:
            return self.refresh
        if status == TaskStatus.FAILED.value:
            return False
        if status == TaskStatus.RETRYABLE_ERROR.value:
            if row["attempt_count"] >= self.max_attempts:
                return False
            due = _parse(row["next_retry"])
            return due is None or due <= _now()
        return status in (TaskStatus.PENDING.value, TaskStatus.RUNNING.value)

    def _runnable_tasks(self):
        tasks = []
        for row in self.db.list_tasks(self.assessment_id, self.snapshot_id):
            if self._is_runnable(row):
                tasks.append(row)
        return tasks

    # -- execution --------------------------------------------------------
    def run(self, specs: list[TaskSpec], executors: dict[str, Executor]) -> SchedulerStats:
        self.ensure_tasks(specs)
        self.reclaim_expired_leases()
        stats = SchedulerStats()

        runnable = self._runnable_tasks()
        # Only run tasks whose collector we were given an executor for.
        runnable = [r for r in runnable if r["collector"] in executors]
        if not runnable:
            return stats

        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {}
            for row in runnable:
                if self._stop.is_set():
                    break
                self._mark_running(row["task_id"], row["attempt_count"])
                futures[pool.submit(self._execute, row, executors[row["collector"]])] = row["task_id"]
            for future in as_completed(futures):
                outcome = future.result()
                self._record(stats, outcome)
        stats.interrupted = self._stop.is_set()
        return stats

    def _mark_running(self, task_id: str, attempt_count: int) -> None:
        expiry = (_now() + timedelta(seconds=LEASE_SECONDS)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self._db_lock:
            self.db.set_task_status(
                task_id,
                status=TaskStatus.RUNNING.value,
                started_at=utcnow(),
                lease_expiry=expiry,
                attempt_count=attempt_count + 1,
            )

    def _execute(self, row, executor: Executor) -> tuple[str, TaskStatus, str]:
        task_id = row["task_id"]
        collector = row["collector"]
        attempt = row["attempt_count"] + 1
        if self._stop.is_set():
            with self._db_lock:
                self.db.set_task_status(task_id, status=TaskStatus.PENDING.value, lease_expiry=None)
            return (collector, TaskStatus.PENDING, task_id)
        try:
            outcome = executor(row["resource_id"])
        except Exception as exc:  # noqa: BLE001 - deliberately broad; classified below
            status, error_class, retry_after = classify_exception(exc)
            outcome = TaskOutcome(status=status, error_class=error_class, error=str(exc), retry_after=retry_after)

        fields: dict[str, object] = {
            "status": outcome.status.value,
            "last_error_class": outcome.error_class,
            "last_error": (outcome.error or "")[:1000] if outcome.error else None,
            "lease_expiry": None,
        }
        if outcome.status in (TaskStatus.SUCCEEDED, TaskStatus.PARTIAL, TaskStatus.UNSUPPORTED,
                              TaskStatus.BLOCKED_PERMISSION, TaskStatus.BLOCKED_NETWORK):
            fields["completed_at"] = utcnow()
        if outcome.status == TaskStatus.RETRYABLE_ERROR:
            delay = self._backoff(attempt, outcome.retry_after)
            fields["next_retry"] = (_now() + timedelta(seconds=delay)).strftime("%Y-%m-%dT%H:%M:%SZ")
            if attempt >= self.max_attempts:
                fields["status"] = TaskStatus.FAILED.value
        with self._db_lock:
            self.db.set_task_status(task_id, **fields)
        return (collector, TaskStatus(fields["status"]), task_id)

    @staticmethod
    def _backoff(attempt: int, retry_after: Optional[float]) -> float:
        if retry_after and retry_after > 0:
            return min(retry_after, 120.0)
        base = min(2 ** attempt, 60)
        return base + random.uniform(0, base * 0.25)

    def _record(self, stats: SchedulerStats, outcome: tuple[str, TaskStatus, str]) -> None:
        collector, status, _task_id = outcome
        bucket = stats.per_collector.setdefault(collector, {})
        bucket[status.value] = bucket.get(status.value, 0) + 1
        if status == TaskStatus.SUCCEEDED:
            stats.succeeded += 1
        elif status == TaskStatus.PARTIAL:
            stats.partial += 1
        elif status in (TaskStatus.BLOCKED_PERMISSION, TaskStatus.BLOCKED_NETWORK, TaskStatus.UNSUPPORTED):
            stats.blocked += 1
        elif status == TaskStatus.FAILED:
            stats.failed += 1
