"""Small shared helpers (JSON I/O, timestamps)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def dumps(data: Any) -> str:
    """Token-lean JSON: one top-level key per line, one array record per line.

    Roughly minified size, yet still line-oriented for human review, diffs and
    grep-by-ID. Non-object documents fall back to compact JSON.
    """
    if not isinstance(data, dict) or not data:
        return _compact(data) + "\n"
    lines = ["{"]
    items = list(data.items())
    for i, (key, value) in enumerate(items):
        tail = "," if i < len(items) - 1 else ""
        head = f"{_compact(key)}:"
        if isinstance(value, list) and value:
            body = ",\n".join(_compact(v) for v in value)
            lines.append(f"{head}[\n{body}\n]{tail}")
        else:
            lines.append(f"{head}{_compact(value)}{tail}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def dump_json(path: Path, data: Any) -> None:
    Path(path).write_text(dumps(data), encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8", newline="\n")
