"""Minimal YAML loader with a PyYAML fast path.

The installed skill must not require third-party packages. This module provides
``safe_load`` for the constrained subset of YAML used by the standard files
(block mappings and sequences, scalars, quoted strings, inline ``[]`` lists,
folded ``>`` block scalars, comments, and ``true``/``false``/``null``/numbers).

If PyYAML is importable it is used instead, so hand-authored standards that use
richer YAML still parse correctly in developer environments.
"""

from __future__ import annotations

from typing import Any

try:  # pragma: no cover - exercised implicitly when PyYAML present
    import yaml as _pyyaml

    def safe_load(text: str) -> Any:
        """Parse YAML text, preferring PyYAML when available."""
        return _pyyaml.safe_load(text)

    _USING_PYYAML = True
except Exception:  # pragma: no cover - fallback path
    _USING_PYYAML = False

    def safe_load(text: str) -> Any:
        return _MiniYaml(text).parse()


def _scalar(token: str) -> Any:
    token = token.strip()
    if token == "" or token == "~" or token.lower() == "null":
        return None
    if token.lower() == "true":
        return True
    if token.lower() == "false":
        return False
    if len(token) >= 2 and token[0] in "'\"" and token[-1] == token[0]:
        return token[1:-1]
    if token.startswith("[") and token.endswith("]"):
        inner = token[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in _split_flow(inner)]
    if token.startswith("{") and token.endswith("}"):
        inner = token[1:-1].strip()
        out: dict[str, Any] = {}
        if inner:
            for part in _split_flow(inner):
                k, _, v = part.partition(":")
                out[_scalar(k)] = _scalar(v)
        return out
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


def _split_flow(inner: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    quote = ""
    current = ""
    for ch in inner:
        if quote:
            current += ch
            if ch == quote:
                quote = ""
            continue
        if ch in "'\"":
            quote = ch
            current += ch
        elif ch in "[{":
            depth += 1
            current += ch
        elif ch in "]}":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current)
    return parts


class _MiniYaml:
    """A tiny indentation-based YAML parser for the standard-file subset."""

    def __init__(self, text: str) -> None:
        self.lines: list[tuple[int, str]] = []
        for raw in text.splitlines():
            stripped = self._strip_comment(raw)
            if stripped.strip() == "":
                continue
            indent = len(stripped) - len(stripped.lstrip(" "))
            self.lines.append((indent, stripped.strip()))
        self.pos = 0

    @staticmethod
    def _strip_comment(line: str) -> str:
        quote = ""
        out = []
        for ch in line:
            if quote:
                out.append(ch)
                if ch == quote:
                    quote = ""
            elif ch in "'\"":
                quote = ch
                out.append(ch)
            elif ch == "#":
                break
            else:
                out.append(ch)
        return "".join(out).rstrip()

    def parse(self) -> Any:
        if not self.lines:
            return None
        return self._parse_block(self.lines[0][0])

    def _parse_block(self, indent: int) -> Any:
        if self.pos >= len(self.lines):
            return None
        first_indent, first = self.lines[self.pos]
        if first.startswith("- "):
            return self._parse_sequence(indent)
        return self._parse_mapping(indent)

    def _parse_mapping(self, indent: int) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while self.pos < len(self.lines):
            cur_indent, cur = self.lines[self.pos]
            if cur_indent < indent:
                break
            if cur_indent > indent:
                break
            if cur.startswith("- "):
                break
            key, sep, rest = cur.partition(":")
            key = _scalar(key.strip())
            rest = rest.strip()
            self.pos += 1
            if rest in (">", "|", ">-", "|-", ">+", "|+"):
                result[key] = self._parse_block_scalar(indent)
            elif rest == "":
                if self.pos < len(self.lines) and self.lines[self.pos][0] > indent:
                    result[key] = self._parse_block(self.lines[self.pos][0])
                else:
                    result[key] = None
            else:
                result[key] = _scalar(rest)
        return result

    def _parse_sequence(self, indent: int) -> list[Any]:
        result: list[Any] = []
        while self.pos < len(self.lines):
            cur_indent, cur = self.lines[self.pos]
            if cur_indent != indent or not cur.startswith("- "):
                break
            item_text = cur[2:].strip()
            if ":" in item_text and not (
                item_text[0] in "'\"[{" or item_text.startswith("- ")
            ):
                # Inline mapping start on the dash line; splice it in.
                self.lines[self.pos] = (indent + 2, item_text)
                result.append(self._parse_mapping(indent + 2))
            elif item_text == "":
                self.pos += 1
                if self.pos < len(self.lines) and self.lines[self.pos][0] > indent:
                    result.append(self._parse_block(self.lines[self.pos][0]))
                else:
                    result.append(None)
            else:
                result.append(_scalar(item_text))
                self.pos += 1
        return result

    def _parse_block_scalar(self, parent_indent: int) -> str:
        collected: list[str] = []
        while self.pos < len(self.lines):
            cur_indent, cur = self.lines[self.pos]
            if cur_indent <= parent_indent:
                break
            collected.append(cur)
            self.pos += 1
        return " ".join(collected)
