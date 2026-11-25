"""Create and inspect a discovery workspace (the output directory).

Layout::

    <out>/
      .gitignore              '*'  - the package never lands in the repo by accident
      _work/                  working state, never packaged (alias map, scans, scope)
      _dist/                  ZIP archives produced by `package`
      *.json, *.md, *.csv     the package
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from . import SCHEMA_VERSION, SKILL_NAME, SKILL_VERSION, profiles, repo_scan, sanitize
from .paths import DIST_DIR_NAME, JSON_FILES, TEMPLATES_DIR, WORK_DIR_NAME
from .util import dump_json, load_json, today, utc_now

TEMPLATE_FILES = {
    "package-README.md": "README.md",
    "discovery-report.md": "discovery-report.md",
    "executive-discovery-summary.md": "executive-discovery-summary.md",
}


class WorkspaceError(RuntimeError):
    pass


def work_dir(out: Path) -> Path:
    return Path(out) / WORK_DIR_NAME


def dist_dir(out: Path) -> Path:
    return Path(out) / DIST_DIR_NAME


def load_scope(out: Path) -> dict[str, Any]:
    path = work_dir(out) / "scope.json"
    if not path.exists():
        raise WorkspaceError(f"{out} is not an initialised workspace; run `ada.py init` first.")
    return load_json(path)


def _relative_inside(child: Path, parent: Path) -> str | None:
    try:
        return child.resolve().relative_to(parent.resolve()).as_posix()
    except ValueError:
        return None


def criterion_skeleton(c) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": c.id,
        "domain": c.domain,
        "title": c.title,
        "question": c.question,
        "source_profile": c.source_profile,
        "emphasis": c.emphasis,
        "applicability": "applicable",
        "status": "unknown",
        "maturity": "U",
        "confidence": "none",
        "discovery_coverage": "not_investigated",
        "evidence_refs": [],
        "discovery_attempts": [],
    }
    if c.expected_baseline:
        item["expected_baseline"] = {
            "statement": c.expected_baseline,
            "source": c.baseline_source or c.source_profile,
            "verified_policy": bool(c.verified_policy),
        }
    if c.follow_up_questions:
        item["follow_up_questions"] = list(c.follow_up_questions)
    return item


def empty_documents(profile_ids: list[str]) -> dict[str, Any]:
    return {
        "evidence.json": {"schema_version": SCHEMA_VERSION, "evidence": []},
        "architecture.json": {"schema_version": SCHEMA_VERSION, "entities": [], "relationships": []},
        "execution-flows.json": {"schema_version": SCHEMA_VERSION, "flows": []},
        "technology-inventory.json": {"schema_version": SCHEMA_VERSION, "items": [], "external_verification": []},
        "workload-characteristics.json": {"schema_version": SCHEMA_VERSION, "characteristics": []},
        "design-decisions.json": {"schema_version": SCHEMA_VERSION, "decisions": []},
        "azure-configuration.json": {"schema_version": SCHEMA_VERSION, "collections": [], "resources": [], "attempts": []},
    }


def manifest_skeleton(resolved, identity: dict[str, Any], languages: dict[str, int]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "skill": {"name": SKILL_NAME, "version": SKILL_VERSION},
        "schema_versions": {name: SCHEMA_VERSION for name in sorted(JSON_FILES)},
        "profiles": [
            {"id": p.id, "version": p.version, "kind": p.kind, "baseline_status": p.baseline_status, "title": p.title}
            for p in resolved.profiles
        ],
        "assessment_date": today(),
        "repository": {
            "name": identity["name"],
            "remote": identity["remote"],
            "revision": identity["revision"],
            "branch": identity["branch"],
            "working_tree_clean": identity["working_tree_clean"],
            "working_tree_summary": identity["working_tree_summary"],
            "languages": languages,
        },
        "discovery_modes": ["repository"],
        "environments_inspected": [],
        "azure_scope": {
            "authorised": False,
            "authorised_by": None,
            "cli_available": None,
            "authenticated": None,
            "scopes": [],
            "telemetry_authorised": False,
            "command_templates": [],
            "failed_attempts": [],
        },
        "evidence_sources_inspected": [],
        "evidence_sources_unavailable": [],
        "external_documentation": [],
        "sanitisation": {"performed": False},
        "limitations": [] if identity["git_available"] else ["Git metadata unavailable; repository revision not recorded."],
        "integrity": {"baseline_status_hash": identity["status_hash"], "repository_unchanged": None, "checked_at": None},
    }


def init(repo: Path, out: Path, profile_refs: list[str], force: bool = False) -> dict[str, Any]:
    repo = Path(repo).resolve()
    out = Path(out)
    if not out.is_absolute():
        out = (Path.cwd() / out)
    out = out.resolve()
    if not repo.is_dir():
        raise WorkspaceError(f"Repository path {repo} does not exist.")

    resolved = profiles.resolve(profile_refs)

    existing = [n for n in list(JSON_FILES) + list(TEMPLATE_FILES.values()) if (out / n).exists()]
    if existing and not force:
        raise WorkspaceError(
            f"{out} already contains package files ({', '.join(existing[:4])}...). Use --force to re-initialise "
            "(overwrites them) or choose another --out."
        )

    out.mkdir(parents=True, exist_ok=True)
    work_dir(out).mkdir(exist_ok=True)
    (out / ".gitignore").write_text("# Discovery output: review before sharing, never commit.\n*\n", encoding="utf-8")

    exclude_rel = _relative_inside(out, repo)
    identity = repo_scan.repo_identity(repo, exclude_rel)
    inventory = repo_scan.scan(repo, exclude=out if exclude_rel else None)

    profiles.dump(resolved, work_dir(out) / "resolved-criteria.json")
    aliases = sanitize.AliasMap(work_dir(out) / "alias-map.json")
    for term, kind in sanitize.identity_terms(identity["name"], identity["remote"]):
        aliases.register_term(term, kind)
    aliases.save()
    identity = {**identity, **{k: sanitize.clean_value(identity[k], aliases) for k in ("name", "remote", "branch")}}
    dump_json(work_dir(out) / "repo-inventory.json", inventory)
    dump_json(work_dir(out) / "scope.json", {
        "repository_path": str(repo),
        "output_path": str(out),
        "output_inside_repository": exclude_rel,
        "profiles": [p.id for p in resolved.profiles],
        "initialised_at": utc_now(),
        "baseline_status_hash": identity["status_hash"],
        "git_available": identity["git_available"],
    })

    for name, doc in empty_documents([p.id for p in resolved.profiles]).items():
        dump_json(out / name, doc)
    dump_json(out / "assessment.json", {
        "schema_version": SCHEMA_VERSION,
        "profiles": [p.id for p in resolved.profiles],
        "criteria": [criterion_skeleton(c) for c in resolved.criteria],
        "observations": [],
        "open_questions": [],
    })
    dump_json(out / "manifest.json", manifest_skeleton(resolved, identity, inventory["languages"]))
    for template, target in TEMPLATE_FILES.items():
        shutil.copyfile(TEMPLATES_DIR / template, out / target)

    return {
        "output": str(out),
        "criteria": len(resolved.criteria),
        "profiles": [p.id for p in resolved.profiles],
        "files_scanned": inventory["file_count"],
        "untrusted_instruction_markers": len(inventory["untrusted_instruction_markers"]),
        "secret_bearing_files_skipped": len(inventory["secret_bearing_files"]),
        "git_available": identity["git_available"],
        "working_tree_clean": identity["working_tree_clean"],
    }


def repository_unchanged(out: Path) -> bool | None:
    scope = load_scope(out)
    baseline = scope.get("baseline_status_hash")
    if baseline is None:
        return None
    repo = Path(scope["repository_path"])
    lines = repo_scan.status_lines(repo, scope.get("output_inside_repository"))
    return repo_scan.status_hash(lines) == baseline


def package_files(out: Path) -> list[Path]:
    """Files that belong in the handover package (excludes working state)."""
    out = Path(out)
    files: list[Path] = []
    for root, dirs, names in os.walk(out):
        rel_root = Path(root).relative_to(out)
        if rel_root.parts and rel_root.parts[0] in (WORK_DIR_NAME, DIST_DIR_NAME):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in (WORK_DIR_NAME, DIST_DIR_NAME) and not d.startswith(".")]
        for name in names:
            if name == ".gitignore" or name.startswith("."):
                continue
            files.append(Path(root) / name)
    return sorted(files)
