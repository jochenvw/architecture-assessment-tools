"""Parse the domain catalogues (references/domains/*.md) into criteria.

The Markdown tables are the single source of truth for generic criteria.
Rows look like: ``| AE-03 | Title | Investigate ... | Evidence ... |``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .paths import DOMAINS_DIR

_ROW = re.compile(r"^\|\s*([A-Z]{2,4}-\d{2,3})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*$")


@dataclass
class Criterion:
    id: str
    domain: str
    title: str
    question: str
    evidence_hints: str = ""
    source_profile: str = "azure-agent"
    expected_baseline: str | None = None
    baseline_source: str | None = None
    verified_policy: bool = False
    emphasis: str = "standard"
    related: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)


def domain_files(domains_dir: Path = DOMAINS_DIR) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for path in sorted(domains_dir.glob("*.md")):
        match = re.match(r"^(\d{2})-", path.name)
        if match:
            out[match.group(1)] = path
    return out


def load_catalogue(domains_dir: Path = DOMAINS_DIR) -> list[Criterion]:
    criteria: list[Criterion] = []
    seen: set[str] = set()
    for domain, path in domain_files(domains_dir).items():
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _ROW.match(line.strip())
            if not match:
                continue
            cid, title, investigate, evidence = match.groups()
            if cid in seen:
                raise ValueError(f"Duplicate criterion id {cid} in {path.name}")
            seen.add(cid)
            criteria.append(Criterion(id=cid, domain=domain, title=title, question=investigate, evidence_hints=evidence))
    return criteria
