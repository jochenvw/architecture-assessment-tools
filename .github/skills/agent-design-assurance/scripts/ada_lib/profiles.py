"""Load, validate and combine assessment profiles.

Profiles compose: one generic profile selects domain catalogues; platform and
workload profiles add their own criteria and emphasis. Customer specifics never
live in the generic catalogue.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import yaml_lite
from .catalogue import Criterion, load_catalogue
from .jsonschema_lite import load_schema, validate
from .paths import PROFILES_DIR, SCHEMAS_DIR

_LEVEL_ORDER = {"standard": 0, "high": 1, "critical": 2}


class ProfileError(ValueError):
    pass


@dataclass
class Profile:
    id: str
    kind: str
    version: str
    title: str
    baseline_status: str
    path: Path
    data: dict[str, Any]


@dataclass
class Resolved:
    profiles: list[Profile]
    criteria: list[Criterion]
    domain_emphasis: dict[str, str] = field(default_factory=dict)
    briefing: list[dict[str, Any]] = field(default_factory=list)
    workload_metrics: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "profiles": [
                {"id": p.id, "kind": p.kind, "version": p.version, "title": p.title, "baseline_status": p.baseline_status}
                for p in self.profiles
            ],
            "domain_emphasis": self.domain_emphasis,
            "criteria": [c.__dict__ for c in self.criteria],
            "briefing": self.briefing,
            "workload_metrics": self.workload_metrics,
        }


def find_profile(ref: str, profiles_dir: Path = PROFILES_DIR) -> Path:
    candidate = Path(ref)
    if candidate.suffix in (".yaml", ".yml") and candidate.exists():
        return candidate
    for folder in (profiles_dir, profiles_dir / "examples"):
        for ext in (".yaml", ".yml"):
            path = folder / f"{ref}{ext}"
            if path.exists():
                return path
    available = sorted(p.stem for p in profiles_dir.rglob("*.y*ml"))
    raise ProfileError(f"Profile '{ref}' not found. Available: {', '.join(available) or 'none'}")


def load_profile(path: Path) -> Profile:
    data = yaml_lite.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProfileError(f"{path}: not a mapping")
    errors = validate(data, load_schema(SCHEMAS_DIR / "profile.schema.json"))
    if errors:
        raise ProfileError(f"{path}: invalid profile\n  " + "\n  ".join(errors[:20]))
    meta = data["profile"]
    prefix = meta.get("criterion_prefix")
    for crit in data.get("criteria", []) or []:
        if prefix and not crit["id"].startswith(prefix + "-"):
            raise ProfileError(f"{path}: criterion {crit['id']} does not use prefix {prefix}-")
    return Profile(meta["id"], meta["kind"], str(meta["version"]), meta["title"], meta["baseline_status"], Path(path), data)


def resolve(refs: list[str], profiles_dir: Path = PROFILES_DIR) -> Resolved:
    if not refs:
        raise ProfileError("Select at least one profile (e.g. azure-agent).")
    profiles = [load_profile(find_profile(r, profiles_dir)) for r in refs]
    ids = [p.id for p in profiles]
    if len(set(ids)) != len(ids):
        raise ProfileError(f"Duplicate profiles selected: {ids}")
    if not any(p.kind == "generic" for p in profiles):
        raise ProfileError("At least one generic profile (e.g. azure-agent) is required.")
    for p in profiles:
        missing = [r for r in p.data["profile"].get("requires", []) or [] if r not in ids]
        if missing:
            raise ProfileError(f"Profile '{p.id}' requires {missing}; add them to --profiles.")

    catalogue = load_catalogue()
    criteria: list[Criterion] = []
    for p in profiles:
        if p.kind == "generic":
            include = set(p.data.get("include_domains") or [])
            for c in catalogue:
                if c.domain in include and all(c.id != x.id for x in criteria):
                    c.source_profile = p.id
                    criteria.append(c)
    by_id = {c.id: c for c in criteria}

    for p in profiles:
        verified = p.baseline_status == "verified_policy"
        for raw in p.data.get("criteria", []) or []:
            if raw["id"] in by_id:
                raise ProfileError(f"Criterion id {raw['id']} from '{p.id}' collides with an existing criterion.")
            crit = Criterion(
                id=raw["id"],
                domain=str(raw["domain"]),
                title=raw["title"],
                question=raw["question"],
                evidence_hints=", ".join(raw.get("evidence_hints") or []),
                source_profile=p.id,
                expected_baseline=raw.get("expected_baseline"),
                baseline_source=raw.get("baseline_source") or p.title,
                verified_policy=verified,
                emphasis=raw.get("emphasis") or "standard",
                related=list(raw.get("related") or []),
                follow_up_questions=list(raw.get("follow_up_questions") or []),
            )
            criteria.append(crit)
            by_id[crit.id] = crit

    domain_emphasis: dict[str, str] = {}
    for p in profiles:
        for item in p.data.get("emphasis") or []:
            target, level = str(item["target"]), item["level"]
            if len(target) == 2:
                if _LEVEL_ORDER[level] > _LEVEL_ORDER.get(domain_emphasis.get(target, "standard"), 0):
                    domain_emphasis[target] = level
            elif target in by_id:
                if _LEVEL_ORDER[level] > _LEVEL_ORDER[by_id[target].emphasis]:
                    by_id[target].emphasis = level
            else:
                raise ProfileError(f"Emphasis target {target} in '{p.id}' is not a selected criterion.")

    for crit in criteria:
        dom = domain_emphasis.get(crit.domain, "standard")
        if _LEVEL_ORDER[dom] > _LEVEL_ORDER[crit.emphasis]:
            crit.emphasis = dom

    all_ids = set(by_id)
    for crit in criteria:
        unknown = [r for r in crit.related if r not in all_ids]
        if unknown:
            raise ProfileError(f"Criterion {crit.id} references unknown related criteria {unknown}.")

    briefing: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    for p in profiles:
        b = p.data.get("briefing") or {}
        for claim in b.get("claims") or []:
            bad = [r for r in claim["verify_with"] if r not in all_ids]
            if bad:
                raise ProfileError(f"Briefing claim {claim['id']} references unknown criteria {bad}.")
            briefing.append({"profile": p.id, **claim})
        for m in p.data.get("workload_metrics") or []:
            metrics.append({"profile": p.id, **m})

    generic_ids = {p.id for p in profiles if p.kind == "generic"}
    criteria.sort(key=lambda c: (c.domain, c.source_profile not in generic_ids, c.id))
    return Resolved(profiles, criteria, domain_emphasis, briefing, metrics)


def dump(resolved: Resolved, path: Path) -> None:
    path.write_text(json.dumps(resolved.to_json(), indent=2) + "\n", encoding="utf-8")
