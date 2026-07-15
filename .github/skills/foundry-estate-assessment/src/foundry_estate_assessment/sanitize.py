"""Evidence sanitization.

Every raw Azure response is passed through :func:`sanitize` before it is
persisted or evaluated. The sanitizer removes credentials, keys, tokens,
connection strings and secret values. It never mutates its input in place.

The design principle: it is always safe to drop or redact a value. The scanner
assesses configuration facts, counts and sizes -- never secret material.
"""

from __future__ import annotations

import copy
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REDACTED = "[REDACTED]"

#: Object keys whose values must always be redacted (case-insensitive, substring).
_SECRET_KEY_SUBSTRINGS = (
    "password",
    "secret",
    "apikey",
    "api_key",
    "accountkey",
    "primarykey",
    "secondarykey",
    "primarymasterkey",
    "secondarymasterkey",
    "adminkey",
    "connectionstring",
    "connstr",
    "authorization",
    "sastoken",
    "saskey",
    "accesskey",
    "clientsecret",
    "certificatepassword",
    "privatekey",
    "sharedaccesskey",
    "subscriptionkey",
    "ocp-apim-subscription-key",
    "token",
    "credential",
    "value",  # Key Vault secret value payloads use "value"
)

#: Keys that legitimately end in a secret substring but are safe to keep.
_SAFE_KEY_EXACT = {
    "tokenlimit",
    "tokencredential",  # a type discriminator, not a secret
}

#: Query-string parameters in URLs that carry SAS signatures / secrets.
_SECRET_QUERY_PARAMS = {"sig", "sig=", "signature", "sv", "se", "sp", "sr", "st", "skt", "ske"}

_SAS_RE = re.compile(r"(?i)(sig|signature)=[^&\s\"']+")
_BEARER_RE = re.compile(r"(?i)bearer\s+[a-z0-9\-\._~\+/]+=*")


def _looks_secret_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in _SAFE_KEY_EXACT:
        return False
    return any(sub in lowered for sub in _SECRET_KEY_SUBSTRINGS)


def _redact_url(value: str) -> str:
    try:
        parts = urlsplit(value)
    except ValueError:
        return value
    if not parts.query:
        return value
    kept = [
        (key, val if key.lower() not in _SECRET_QUERY_PARAMS else REDACTED)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(parts._replace(query=urlencode(kept)))


def _sanitize_str(value: str) -> str:
    value = _SAS_RE.sub(lambda m: f"{m.group(1)}={REDACTED}", value)
    value = _BEARER_RE.sub(f"Bearer {REDACTED}", value)
    if "://" in value and ("?" in value):
        value = _redact_url(value)
    # Redact key=value connection-string fragments carrying secrets.
    if "AccountKey=" in value or "SharedAccessKey=" in value or "AccountKey =" in value:
        value = re.sub(
            r"(?i)(AccountKey|SharedAccessKey)\s*=\s*[^;]+",
            lambda m: f"{m.group(1)}={REDACTED}",
            value,
        )
    return value


def sanitize(obj: Any) -> Any:
    """Return a deep-copied, sanitized version of ``obj``.

    Dictionaries have secret-bearing keys redacted; strings have inline
    signatures and bearer tokens stripped; the input is never modified.
    """
    return _sanitize(copy.deepcopy(obj))


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[Any, Any] = {}
        for key, val in obj.items():
            if isinstance(key, str) and _looks_secret_key(key):
                out[key] = REDACTED
            else:
                out[key] = _sanitize(val)
        return out
    if isinstance(obj, list):
        return [_sanitize(item) for item in obj]
    if isinstance(obj, str):
        return _sanitize_str(obj)
    return obj


def contains_secret_markers(text: str) -> bool:
    """Best-effort check used by tests to prove secrets were not persisted."""
    lowered = text.lower()
    markers = ("sig=", "sharedaccesskey=", "accountkey=", "bearer ey")
    return any(marker in lowered for marker in markers)
