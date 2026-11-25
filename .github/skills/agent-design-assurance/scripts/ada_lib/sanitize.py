"""Information-protection pass over the output package.

Two kinds of handling:

* **Redact** secrets (keys, tokens, connection-string credentials, SAS
  signatures, private keys) -> ``[REDACTED-<KIND>]``.
* **Alias** identifiers (ARM IDs, subscription/tenant/principal GUIDs, Azure
  resource, resource-group and host names, e-mail addresses, public IPv4
  addresses, and internal terms such as the repository, organisation, product
  and team names) ->
  stable aliases recorded in ``_work/alias-map.json`` so relationships remain
  understandable while the real values never leave the workspace.

Some content cannot be fixed mechanically (financial figures, verbatim prompts,
PII in prose). Those are reported as ``manual_review`` findings that block
packaging until they are rewritten or explicitly allow-listed in
``_work/sanitize-allowlist.json`` with a reason.
"""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .util import dump_json, load_json

TEXT_SUFFIXES = {".json", ".md", ".csv", ".txt", ".mmd", ".mermaid", ".svg", ".puml", ".dot", ".excalidraw", ".yaml", ".yml"}

AZURE_HOST_SUFFIXES = [
    "openai.azure.com", "cognitiveservices.azure.com", "services.ai.azure.com", "search.windows.net",
    "blob.core.windows.net", "dfs.core.windows.net", "file.core.windows.net", "queue.core.windows.net",
    "table.core.windows.net", "web.core.windows.net", "vault.azure.net", "documents.azure.com", "azurewebsites.net",
    "scm.azurewebsites.net", "azurecontainerapps.io", "azure-api.net", "azurecr.io", "servicebus.windows.net",
    "database.windows.net", "postgres.database.azure.com", "mysql.database.azure.com", "redis.cache.windows.net",
    "azconfig.io", "azurefd.net", "trafficmanager.net", "cloudapp.azure.com", "eventgrid.azure.net",
    "api.azureml.ms", "instances.azureml.ms", "inference.ml.azure.com", "azurestaticapps.net", "applicationinsights.azure.com",
    "monitor.azure.com",
]
GENERIC_HOST_PREFIXES = {
    "privatelink", "management", "login", "graph", "portal", "learn", "docs", "api", "www", "ml", "eastus", "westeurope",
    "northeurope", "swedencentral", "uksouth", "francecentral", "westus", "westus3", "eastus2", "example", "contoso", "fabrikam",
}
SAFE_EMAIL_DOMAINS = re.compile(r"@(example\.(com|org|net)|[a-z0-9.-]+\.invalid|contoso\.com|fabrikam\.com|users\.noreply\.github\.com)$", re.I)
GUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

TYPE_TOKENS = {
    "microsoft.cognitiveservices/accounts/projects": "AIPROJ",
    "microsoft.cognitiveservices/accounts": "AISVC",
    "microsoft.search/searchservices": "SEARCH",
    "microsoft.storage/storageaccounts": "ST",
    "microsoft.documentdb/databaseaccounts": "COSMOS",
    "microsoft.keyvault/vaults": "KV",
    "microsoft.web/sites": "APP",
    "microsoft.web/serverfarms": "PLAN",
    "microsoft.app/containerapps": "CA",
    "microsoft.app/managedenvironments": "CAE",
    "microsoft.app/jobs": "CAJOB",
    "microsoft.apimanagement/service": "APIM",
    "microsoft.insights/components": "APPI",
    "microsoft.operationalinsights/workspaces": "LAW",
    "microsoft.network/privateendpoints": "PE",
    "microsoft.network/virtualnetworks": "VNET",
    "microsoft.network/virtualnetworks/subnets": "SNET",
    "microsoft.network/networksecuritygroups": "NSG",
    "microsoft.network/privatednszones": "PDNS",
    "microsoft.network/networkinterfaces": "NIC",
    "microsoft.network/publicipaddresses": "PIP",
    "microsoft.network/applicationgateways": "AGW",
    "microsoft.network/azurefirewalls": "AFW",
    "microsoft.network/frontdoors": "AFD",
    "microsoft.cdn/profiles": "AFD",
    "microsoft.containerregistry/registries": "ACR",
    "microsoft.machinelearningservices/workspaces": "MLW",
    "microsoft.managedidentity/userassignedidentities": "UAMI",
    "microsoft.servicebus/namespaces": "SB",
    "microsoft.eventhub/namespaces": "EH",
    "microsoft.eventgrid/topics": "EG",
    "microsoft.sql/servers": "SQL",
    "microsoft.dbforpostgresql/flexibleservers": "PG",
    "microsoft.cache/redis": "REDIS",
    "microsoft.appconfiguration/configurationstores": "APPCS",
    "microsoft.logic/workflows": "LOGIC",
    "microsoft.datafactory/factories": "ADF",
    "microsoft.containerservice/managedclusters": "AKS",
    "microsoft.botservice/botservices": "BOT",
}


def type_token(resource_type: str | None) -> str:
    if not resource_type:
        return "RES"
    return TYPE_TOKENS.get(resource_type.lower(), "RES")


MIN_TERM_LENGTH = 4
TERM_KINDS = ("ORG", "APP", "TEAM", "SYSTEM", "PERSON", "TERM")
# Public names that must stay readable even if they appear in a remote URL.
PUBLIC_TERMS = {
    "microsoft", "azure", "azure-samples", "azuread", "github", "gitlab", "bitbucket", "contoso", "fabrikam",
    "example", "origin", "main", "master", "develop", "source", "repo", "repos", "tools", "visualstudio", "_git",
}


def identity_terms(name: str | None, remote: str | None) -> list[tuple[str, str]]:
    """Repository name and remote owner/project/repo segments as (term, kind) pairs."""
    terms: list[tuple[str, str]] = []
    if name:
        terms.append((name, "APP"))
    if remote:
        url = re.sub(r"^[a-z+]+://", "", remote.strip(), flags=re.I)
        url = url.split("@", 1)[-1]
        host, _, path = url.replace(":", "/", 1).partition("/") if "/" in url or ":" in url else (url, "", "")
        segments = [s for s in path.split("/") if s and s.lower() not in ("_git", "scm")]
        if segments:
            segments[-1] = re.sub(r"\.git$", "", segments[-1], flags=re.I)
        if host.lower().endswith(".visualstudio.com"):
            segments.insert(0, host.split(".")[0])
        for i, seg in enumerate(segments):
            terms.append((seg, "APP" if i == len(segments) - 1 else "ORG"))
    return terms


class AliasMap:
    """Stable original -> alias mapping persisted in the workspace (never packaged)."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.by_value: dict[str, str] = {}
        self.counters: dict[str, int] = {}
        if path and Path(path).exists():
            data = load_json(path)
            self.by_value = data.get("by_value", {})
            self.counters = data.get("counters", {})

    def alias(self, value: str, prefix: str, case_insensitive: bool = True) -> str:
        key = value.lower() if case_insensitive else value
        if key in self.by_value:
            return self.by_value[key]
        self.counters[prefix] = self.counters.get(prefix, 0) + 1
        alias = f"{prefix}-{self.counters[prefix]}"
        self.by_value[key] = alias
        return alias

    def known_names(self) -> dict[str, str]:
        """Plain resource names registered by Azure collection (``name:`` keys)."""
        return {k[5:]: v for k, v in self.by_value.items() if k.startswith("name:")}

    def register_name(self, name: str, alias: str) -> None:
        self.by_value[f"name:{name.lower()}"] = alias

    def register_term(self, term: str, prefix: str) -> str | None:
        """Alias an internal name (organisation, product, team, system) wherever it appears."""
        term = term.strip()
        if len(term) < MIN_TERM_LENGTH or term.lower() in PUBLIC_TERMS:
            return None
        return self.alias(f"name:{term}", prefix)

    def save(self) -> None:
        if self.path:
            dump_json(self.path, {"note": "Real identifiers -> aliases. Never share this file.", "by_value": self.by_value, "counters": self.counters})


@dataclass
class Finding:
    file: str
    line: int
    kind: str
    severity: str  # secret | identifier | manual_review
    excerpt: str
    allowlisted: bool = False
    resolved: bool = False


@dataclass
class Rule:
    kind: str
    severity: str
    pattern: re.Pattern[str]
    replace: Callable[[re.Match[str], AliasMap], str] | None = None


def _redact(kind: str, group: int | None = None):
    def _fn(m: re.Match[str], _a: AliasMap) -> str:
        if group is None:
            return f"[REDACTED-{kind}]"
        return m.group(0)[: m.start(group) - m.start(0)] + f"[REDACTED-{kind}]" + m.group(0)[m.end(group) - m.start(0):]
    return _fn


def _alias_arm(m: re.Match[str], a: AliasMap) -> str:
    text = m.group(0)
    parts = text.strip("/").split("/")
    out: list[str] = []
    i = 0
    rtype: list[str] = []
    while i < len(parts):
        seg = parts[i]
        low = seg.lower()
        if low == "subscriptions" and i + 1 < len(parts):
            out += [seg, a.alias(parts[i + 1], "AZ-SUB")]
            i += 2
        elif low == "resourcegroups" and i + 1 < len(parts):
            rg = parts[i + 1]
            out += [seg, rg if re.fullmatch(r"AZ-[A-Z0-9-]+", rg) else a.alias("rg:" + rg, "AZ-RG")]
            i += 2
        elif low == "providers" and i + 1 < len(parts):
            rtype = [parts[i + 1]]
            out += [seg, parts[i + 1]]
            i += 2
            while i + 1 < len(parts):
                rtype.append(parts[i])
                name = parts[i + 1]
                full_type = "/".join([rtype[0], *[t for t in rtype[1:]]])
                alias = name if re.fullmatch(r"AZ-[A-Z0-9-]+", name) else a.alias(f"name:{name}", "AZ-" + type_token(full_type))
                out += [parts[i], alias]
                i += 2
            if i < len(parts):
                out.append(parts[i])
                i += 1
        else:
            out.append(seg)
            i += 1
    return "/" + "/".join(out)


def _alias_host(m: re.Match[str], a: AliasMap) -> str:
    prefix, suffix = m.group(1), m.group(2)
    if prefix.lower() in GENERIC_HOST_PREFIXES or prefix.lower().startswith("az-"):
        return m.group(0)
    known = a.known_names().get(prefix.lower())
    alias = known or a.alias(f"name:{prefix}", "AZ-HOST")
    return f"{alias.lower()}.{suffix}"


def _alias_guid(m: re.Match[str], a: AliasMap) -> str:
    if m.group(0) == "00000000-0000-0000-0000-000000000000":
        return m.group(0)
    return a.alias(m.group(0), "AZ-GUID")


def _alias_email(m: re.Match[str], a: AliasMap) -> str:
    if SAFE_EMAIL_DOMAINS.search(m.group(0)):
        return m.group(0)
    return a.alias(m.group(0), "PERSON") .lower() + "@example.invalid"


def _alias_ip(m: re.Match[str], a: AliasMap) -> str:
    return a.alias(m.group(0), "IP")


def _is_public_ip(text: str, start: int, value: str) -> bool:
    before = text[max(0, start - 16):start].lower()
    if "version" in before or before.endswith("v") or before.endswith("."):
        return False
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return ip.is_global


PLACEHOLDER = re.compile(r"^(<[^>]*>|\$\{?[A-Za-z_]+\}?|\{\{.*\}\}|\*+|x+|\.\.\.|\[REDACTED[^\]]*\]|null|none|true|false|changeme|redacted|your[-_a-z]*|env:.*|os\.environ.*|process\.env.*)$", re.I)

RULES: list[Rule] = [
    Rule("private_key", "secret", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), _redact("PRIVATE-KEY")),
    Rule("connection_string_secret", "secret", re.compile(r"(?i)\b(AccountKey|SharedAccessKey|SharedAccessSignature|Password|Pwd|ApiKey)\s*=\s*([^;\"'\s,]{6,})"), _redact("SECRET", 2)),
    Rule("sas_signature", "secret", re.compile(r"(?i)([?&]sig=)([A-Za-z0-9%+/=]{16,})"), _redact("SAS", 2)),
    Rule("jwt", "secret", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    Rule("bearer_token", "secret", re.compile(r"(?i)\bBearer\s+([A-Za-z0-9\-._~+/]{20,}=*)"), _redact("TOKEN", 1)),
    Rule("github_token", "secret", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"), None),
    Rule("aws_access_key", "secret", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), None),
    Rule("azure_key_base64", "secret", re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{86}==(?![A-Za-z0-9+/=])"), None),
    Rule("generic_secret_assignment", "secret", re.compile(
        r"(?i)\b(api[_-]?key|apikey|secret|client[_-]?secret|password|passwd|access[_-]?token|auth[_-]?token|subscription[_-]?key|primary[_-]?key|secondary[_-]?key)\b[\"']?\s*[:=]\s*[\"']?([^\s\"',;}{)]{8,})"), None),
    Rule("arm_resource_id", "identifier", re.compile(r"(?i)/subscriptions/" + GUID + r"(?:/[A-Za-z0-9._()\-]+)*"), _alias_arm),
    Rule("azure_host", "identifier", re.compile(r"(?i)\b([a-z0-9][a-z0-9-]{1,62})\.(" + "|".join(re.escape(s) for s in sorted(AZURE_HOST_SUFFIXES, key=len, reverse=True)) + r")\b"), _alias_host),
    Rule("guid", "identifier", re.compile(r"\b" + GUID + r"\b"), _alias_guid),
    Rule("email", "identifier", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), _alias_email),
    Rule("public_ipv4", "identifier", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), _alias_ip),
    Rule("financial_figure", "manual_review", re.compile(
        r"(?i)(?:[$€£]\s?\d[\d,.]*\d?\s?(?:k|m|bn|mn|million|billion)?\b|\b(?:USD|EUR|GBP)\s?\d[\d,.]*\s?(?:k|m|bn|mn|million|billion)?\b|\b\d[\d,.]*\s?(?:million|billion|bn|mn)\s+(?:USD|EUR|GBP|dollars|euros|pounds)\b)"), None),
]

_SECRET_DEFAULT = {"private_key": "PRIVATE-KEY", "jwt": "TOKEN", "github_token": "TOKEN", "aws_access_key": "KEY", "azure_key_base64": "KEY"}


def _applicable(rule: Rule, m: re.Match[str], text: str) -> bool:
    if rule.severity == "secret" and "[REDACTED" in m.group(0):
        return False
    if rule.kind == "generic_secret_assignment":
        value = m.group(2).strip()
        return not PLACEHOLDER.match(value) and not value.startswith(("[REDACTED", "AZ-", "{", "$"))
    if rule.kind == "public_ipv4":
        return _is_public_ip(text, m.start(), m.group(0))
    if rule.kind == "email":
        return not SAFE_EMAIL_DOMAINS.search(m.group(0))
    if rule.kind == "azure_host":
        p = m.group(1).lower()
        return p not in GENERIC_HOST_PREFIXES and not p.startswith("az-")
    if rule.kind == "guid":
        return m.group(0) != "00000000-0000-0000-0000-000000000000"
    return True


def _replacement(rule: Rule, m: re.Match[str], aliases: AliasMap) -> str:
    if rule.replace:
        return rule.replace(m, aliases)
    if rule.kind == "generic_secret_assignment":
        return _redact("SECRET", 2)(m, aliases)
    return f"[REDACTED-{_SECRET_DEFAULT.get(rule.kind, 'SECRET')}]"


@dataclass
class Result:
    findings: list[Finding] = field(default_factory=list)
    aliases_applied: int = 0
    secrets_redacted: int = 0
    files_changed: list[str] = field(default_factory=list)

    @property
    def blocking(self) -> list[Finding]:
        return [f for f in self.findings if not f.allowlisted and not f.resolved]


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def _excerpt(value: str, severity: str) -> str:
    value = value.replace("\n", " ")
    if severity == "secret":
        return value[:4] + "..." if len(value) > 4 else "..."
    return value[:60]


def _load_allowlist(path: Path | None) -> list[dict[str, Any]]:
    if not path or not Path(path).exists():
        return []
    data = load_json(path)
    items = data.get("allow", data) if isinstance(data, dict) else data
    return [i for i in items if isinstance(i, dict) and i.get("match") and i.get("reason")]


def _allowlisted(allow: list[dict[str, Any]], file: str, match: str) -> bool:
    for item in allow:
        if item["match"] in match or match in item["match"]:
            if not item.get("file") or item["file"] == file:
                return True
    return False


def process_text(text: str, file: str, aliases: AliasMap, allow: list[dict[str, Any]], apply: bool, result: Result) -> str:
    for name, alias in sorted(aliases.known_names().items(), key=lambda kv: -len(kv[0])):
        if len(name) < 4:
            continue
        rx = re.compile(r"(?<![A-Za-z0-9-])" + re.escape(name) + r"(?![A-Za-z0-9-])", re.I)
        for m in rx.finditer(text):
            result.findings.append(Finding(file, _line_of(text, m.start()), "known_resource_name", "identifier", m.group(0)[:60], resolved=apply))
        if apply:
            text, n = rx.subn(alias, text)
            result.aliases_applied += n

    for rule in RULES:
        pieces: list[str] = []
        last = 0
        for m in rule.pattern.finditer(text):
            if not _applicable(rule, m, text):
                continue
            allowed = _allowlisted(allow, file, m.group(0))
            fixable = apply and not allowed and rule.severity != "manual_review"
            result.findings.append(Finding(file, _line_of(text, m.start()), rule.kind, rule.severity, _excerpt(m.group(0), rule.severity), allowed, fixable))
            if fixable:
                pieces.append(text[last:m.start()])
                pieces.append(_replacement(rule, m, aliases))
                last = m.end()
                if rule.severity == "secret":
                    result.secrets_redacted += 1
                else:
                    result.aliases_applied += 1
        if apply and pieces:
            pieces.append(text[last:])
            text = "".join(pieces)
    return text


def run(files: list[Path], base: Path, aliases: AliasMap, allowlist: Path | None, apply: bool) -> tuple[Result, list[str]]:
    allow = _load_allowlist(allowlist)
    result = Result()
    excluded: list[str] = []
    for path in files:
        rel = path.relative_to(base).as_posix()
        if path.suffix.lower() not in TEXT_SUFFIXES:
            excluded.append(rel)
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        updated = process_text(original, rel, aliases, allow, apply, result)
        if apply and updated != original:
            path.write_text(updated, encoding="utf-8", newline="")
            result.files_changed.append(rel)
    return result, excluded


def clean_value(value: Any, aliases: AliasMap) -> Any:
    """Alias/redact every string inside a JSON-like value (used by Azure collection)."""
    if isinstance(value, str):
        scratch = Result()
        return process_text(value, "<azure>", aliases, [], True, scratch)
    if isinstance(value, list):
        return [clean_value(v, aliases) for v in value]
    if isinstance(value, dict):
        return {k: clean_value(v, aliases) for k, v in value.items()}
    return value
