"""Evidence persistence.

Handles writing sanitized raw Azure responses to disk (with SHA-256 provenance)
and building normalized evidence records for the database. Raw writing is
skipped entirely when ``--no-raw-evidence`` is set.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from . import __version__
from .sanitize import sanitize

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def utcnow() -> str:
    """Return an ISO-8601 UTC timestamp with second precision."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_filename(resource_id: str, collector: str) -> str:
    slug = _SAFE_NAME_RE.sub("_", resource_id).strip("_")
    if len(slug) > 150:
        digest = hashlib.sha256(resource_id.encode("utf-8")).hexdigest()[:12]
        slug = slug[:130] + "_" + digest
    return f"{slug}__{collector}.json"


def atomic_write(path: Path, text: str) -> None:
    """Write text atomically so an interrupt never leaves a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


class EvidenceStore:
    """Writes sanitized raw evidence and returns provenance metadata."""

    def __init__(self, raw_dir: Path, no_raw_evidence: bool = False) -> None:
        self.raw_dir = Path(raw_dir)
        self.no_raw_evidence = no_raw_evidence

    def persist_raw(
        self,
        resource_id: str,
        collector: str,
        raw: Any,
        api_version: Optional[str] = None,
    ) -> dict[str, Optional[str]]:
        """Sanitize and persist a raw response; return provenance fields.

        Returns a dict with ``raw_path``, ``raw_sha256``, ``api_version``,
        ``collected_at`` and ``collector_version``. When raw evidence is
        disabled the hash is still computed (for change detection) but no file
        is written.
        """
        clean = sanitize(raw)
        serialized = json.dumps(clean, sort_keys=True, ensure_ascii=False, indent=2)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        raw_path: Optional[str] = None
        if not self.no_raw_evidence:
            target = self.raw_dir / _safe_filename(resource_id, collector)
            atomic_write(target, serialized)
            raw_path = str(target)
        return {
            "raw_path": raw_path,
            "raw_sha256": digest,
            "api_version": api_version,
            "collected_at": utcnow(),
            "collector_version": __version__,
        }
