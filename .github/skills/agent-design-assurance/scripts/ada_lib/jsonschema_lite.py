"""Small JSON Schema validator (draft 2020-12 subset), stdlib only.

Supported keywords: type, enum, const, properties, required,
additionalProperties, items, minItems, uniqueItems, minLength, pattern,
minimum, maximum, $ref (local "#/$defs/..."), anyOf, oneOf, allOf.
Unknown keywords (title, description, format, examples, ...) are ignored.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def load_schema(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Return a list of human-readable errors; empty when valid."""
    errors: list[str] = []
    _validate(instance, schema, schema, "$", errors)
    return errors


def _resolve(ref: str, root: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"Only local $ref supported: {ref}")
    node: Any = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _validate(inst: Any, schema: Any, root: dict[str, Any], path: str, errors: list[str]) -> None:
    if schema is True or schema == {}:
        return
    if schema is False:
        errors.append(f"{path}: not allowed")
        return
    if "$ref" in schema:
        _validate(inst, _resolve(schema["$ref"], root), root, path, errors)

    expected = schema.get("type")
    if expected is not None:
        types = expected if isinstance(expected, list) else [expected]
        if not any(_TYPES[t](inst) for t in types):
            errors.append(f"{path}: expected {'/'.join(types)}, got {type(inst).__name__}")
            return

    if "const" in schema and inst != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and inst not in schema["enum"]:
        errors.append(f"{path}: {inst!r} not in {schema['enum']}")

    if isinstance(inst, str):
        if "minLength" in schema and len(inst) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errors.append(f"{path}: {inst!r} does not match {schema['pattern']}")

    if isinstance(inst, (int, float)) and not isinstance(inst, bool):
        if "minimum" in schema and inst < schema["minimum"]:
            errors.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and inst > schema["maximum"]:
            errors.append(f"{path}: above maximum {schema['maximum']}")

    if isinstance(inst, dict):
        for key in schema.get("required", []):
            if key not in inst:
                errors.append(f"{path}: missing required property '{key}'")
        props = schema.get("properties", {})
        for key, value in inst.items():
            if key in props:
                _validate(value, props[key], root, f"{path}.{key}", errors)
            else:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append(f"{path}: unexpected property '{key}'")
                elif isinstance(extra, dict):
                    _validate(value, extra, root, f"{path}.{key}", errors)

    if isinstance(inst, list):
        if "minItems" in schema and len(inst) < schema["minItems"]:
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if schema.get("uniqueItems"):
            seen = [json.dumps(i, sort_keys=True) for i in inst]
            if len(seen) != len(set(seen)):
                errors.append(f"{path}: items are not unique")
        if "items" in schema:
            for i, item in enumerate(inst):
                _validate(item, schema["items"], root, f"{path}[{i}]", errors)

    for keyword in ("allOf",):
        for sub in schema.get(keyword, []):
            _validate(inst, sub, root, path, errors)
    if "anyOf" in schema:
        if not any(not validate_sub(inst, s, root) for s in schema["anyOf"]):
            errors.append(f"{path}: does not match any allowed shape")
    if "oneOf" in schema:
        matches = sum(1 for s in schema["oneOf"] if not validate_sub(inst, s, root))
        if matches != 1:
            errors.append(f"{path}: must match exactly one allowed shape (matched {matches})")


def validate_sub(inst: Any, schema: Any, root: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    _validate(inst, schema, root, "$", errs)
    return errs
