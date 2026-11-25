"""Assemble the handover ZIP. Never uploads, sends or commits anything."""

from __future__ import annotations

import hashlib
import re
import zipfile
from pathlib import Path
from typing import Any

from . import checks, sanitize, workspace
from .util import dump_json, load_json, utc_now

ZIP_TEXT_SUFFIXES = sanitize.TEXT_SUFFIXES


class PackageError(RuntimeError):
    pass


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "application"


def build(out: Path, allow_incomplete: bool = False, allow_repo_changes: bool = False) -> dict[str, Any]:
    out = Path(out)
    issues = checks.run(out, allow_incomplete=allow_incomplete, allow_repo_changes=allow_repo_changes)
    errors = [i for i in issues if i.level == "error"]
    if errors:
        raise PackageError("Quality gates failed; run `ada.py check` and resolve:\n  " + "\n  ".join(str(e) for e in errors[:30]))

    manifest = load_json(out / "manifest.json")
    files = workspace.package_files(out)
    excluded = [f.relative_to(out).as_posix() for f in files if f.suffix.lower() not in ZIP_TEXT_SUFFIXES]
    included = [f for f in files if f.suffix.lower() in ZIP_TEXT_SUFFIXES]

    san = manifest.setdefault("sanitisation", {"performed": False})
    san["performed"] = True
    san["performed_at"] = san.get("performed_at") or utc_now()
    san["tool"] = "ada.py sanitize + package scan"
    san["files_excluded"] = sorted(set(san.get("files_excluded", []) + excluded))
    if workspace.work_dir(out).joinpath("scope.json").exists():
        unchanged = workspace.repository_unchanged(out)
        manifest["integrity"]["repository_unchanged"] = unchanged
        manifest["integrity"]["checked_at"] = utc_now()
    dump_json(out / "manifest.json", manifest)

    # Re-scan after the manifest update: the final archive must be clean.
    result, _ = sanitize.run(included, out, sanitize.AliasMap(workspace.work_dir(out) / "alias-map.json"),
                             workspace.work_dir(out) / "sanitize-allowlist.json", apply=False)
    if result.blocking:
        raise PackageError(f"{len(result.blocking)} unresolved sensitive findings; run `ada.py sanitize`.")

    name = f"{_slug(manifest['repository']['name'])}-design-assurance-{manifest['assessment_date']}.zip"
    dist = workspace.dist_dir(out)
    dist.mkdir(exist_ok=True)
    target = dist / name
    root = Path(name).stem
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in included:
            rel = path.relative_to(out).as_posix()
            info = zipfile.ZipInfo(f"{root}/{rel}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (dist / (name + ".sha256")).write_text(f"{digest}  {name}\n", encoding="utf-8")
    return {
        "archive": str(target),
        "sha256": digest,
        "files": len(included),
        "excluded": excluded,
        "warnings": [str(i) for i in issues if i.level == "warning"],
    }
