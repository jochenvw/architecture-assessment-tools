"""Rule engine: evaluate collected evidence against a configurable standard.

The standard is defined in YAML (``standards/standard-foundry-v1.yaml``) and
loaded here. Rule evaluation is deterministic and performs no Azure calls, so
``reevaluate`` can re-run a changed standard against previously collected
evidence.

Supported assertion operators (documented in ``references/rule-authoring.md``):

    equals, equals_parameter, in, in_parameter, exists, not_exists,
    greater_than, less_than, count_equals, count_greater_than,
    relationship_exists, any_related_resource_matches,
    all_related_resources_match

Unknown or unavailable evidence never becomes ``FAIL``; it becomes ``UNKNOWN``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .database import Database
from .evidence import utcnow
from .models import EffectiveResult, Finding, RuleResult
from .yaml_lite import safe_load

_MISSING = object()
_UNKNOWN_TOKENS = {"unknown", "unavailable", "not-collected"}


@dataclass
class Rule:
    id: str
    title: str
    category: str
    severity: str
    applies_to: list[str]
    evidence: dict[str, Any]
    assertion: dict[str, Any]
    recommended_investigation: str = ""


@dataclass
class Standard:
    metadata: dict[str, Any]
    parameters: dict[str, Any]
    rules: list[Rule]
    exceptions: list[dict[str, Any]] = field(default_factory=list)
    effort: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return str(self.metadata.get("id", "unknown-standard"))

    @property
    def version(self) -> str:
        return str(self.metadata.get("version", "0"))


def load_standard(path: Path) -> Standard:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = safe_load(handle.read()) or {}
    rules = [
        Rule(
            id=r["id"],
            title=r.get("title", r["id"]),
            category=r.get("category", "general"),
            severity=r.get("severity", "medium"),
            applies_to=list(r.get("applies_to", []) or []),
            evidence=r.get("evidence", {}) or {},
            assertion=r.get("assertion", {}) or {},
            recommended_investigation=r.get("recommended_investigation", ""),
        )
        for r in (data.get("rules") or [])
    ]
    return Standard(
        metadata=data.get("metadata", {}) or {},
        parameters=data.get("parameters", {}) or {},
        rules=rules,
        exceptions=list(data.get("exceptions", []) or []),
        effort=data.get("effort", {}) or {},
    )


def _resolve_path(doc: dict[str, Any], path: str) -> Any:
    current: Any = doc
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


class EvidenceView:
    """Per-Foundry assembled evidence: facts, statuses and relationships."""

    def __init__(
        self,
        foundry_id: str,
        evidence_by_resource: dict[str, dict[str, dict[str, Any]]],
        status_by_resource: dict[str, dict[str, str]],
        rels_from: dict[str, list[dict[str, Any]]],
    ) -> None:
        self.foundry_id = foundry_id
        self._evidence = evidence_by_resource
        self._status = status_by_resource
        self._rels_from = rels_from
        self.doc = evidence_by_resource.get(foundry_id, {})
        # Foundry + its project ids act as relationship sources.
        self._sources = {foundry_id}
        for rel in rels_from.get(foundry_id, []):
            if rel["relationship_type"] == "FOUNDRY_HAS_PROJECT":
                self._sources.add(rel["target_id"])

    def has_collected_evidence(self) -> bool:
        """True if any collector produced usable evidence for this Foundry.

        Used to distinguish "relationship genuinely absent" (FAIL) from "not yet
        collected" (UNKNOWN): absence can only be asserted once collection ran.
        """
        for collector, status in self._status.get(self.foundry_id, {}).items():
            if status in ("SUCCEEDED", "PARTIAL"):
                return True
        return False

    def get(self, path: str) -> Any:
        collector = path.split(".", 1)[0]
        status = self._status.get(self.foundry_id, {}).get(collector)
        if status is not None and status not in ("SUCCEEDED", "PARTIAL"):
            return _MISSING
        return _resolve_path(self.doc, path)

    def relationships(self, types: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for source in self._sources:
            for rel in self._rels_from.get(source, []):
                if rel["relationship_type"] in types:
                    out.append(rel)
        return out

    def related_resource_docs(self, types: list[str]) -> list[dict[str, Any]]:
        docs = []
        seen: set[str] = set()
        for rel in self.relationships(types):
            target = rel["target_id"]
            if target in seen:
                continue
            seen.add(target)
            # Expose related evidence under two addressing schemes so rules can
            # use either the collector-prefixed path (e.g. ``apim.isV2``) or the
            # bare field name (e.g. ``disableLocalAuth``). Collector-keyed
            # entries win on collision.
            resource_evidence = self._evidence.get(target, {})
            merged: dict[str, Any] = {}
            for facts in resource_evidence.values():
                if isinstance(facts, dict):
                    merged.update(facts)
            merged.update(resource_evidence)
            docs.append(merged)
        return docs


def _is_unknown_value(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() in _UNKNOWN_TOKENS


def _apply_operator(assertion: dict[str, Any], value: Any, params: dict[str, Any]) -> tuple[RuleResult, Any]:
    """Evaluate a scalar assertion; returns (result, expected)."""
    if "equals" in assertion:
        expected = assertion["equals"]
        if value is _MISSING or _is_unknown_value(value):
            return RuleResult.UNKNOWN, expected
        return (RuleResult.PASS if value == expected else RuleResult.FAIL), expected
    if "equals_parameter" in assertion:
        expected = params.get(assertion["equals_parameter"])
        if value is _MISSING or _is_unknown_value(value):
            return RuleResult.UNKNOWN, expected
        return (RuleResult.PASS if value == expected else RuleResult.FAIL), expected
    if "in" in assertion:
        expected = assertion["in"]
        if value is _MISSING or _is_unknown_value(value):
            return RuleResult.UNKNOWN, expected
        return (RuleResult.PASS if value in expected else RuleResult.FAIL), expected
    if "in_parameter" in assertion:
        expected = params.get(assertion["in_parameter"], [])
        if value is _MISSING or _is_unknown_value(value):
            return RuleResult.UNKNOWN, expected
        return (RuleResult.PASS if value in expected else RuleResult.FAIL), expected
    if "contains" in assertion:
        needle = assertion["contains"]
        if value is _MISSING or not isinstance(value, (list, tuple)):
            return RuleResult.UNKNOWN, f"contains {needle}"
        return (RuleResult.PASS if needle in value else RuleResult.FAIL), f"contains {needle}"
    if "contains_parameter" in assertion:
        needle = params.get(assertion["contains_parameter"])
        if value is _MISSING or not isinstance(value, (list, tuple)):
            return RuleResult.UNKNOWN, f"contains {needle}"
        return (RuleResult.PASS if needle in value else RuleResult.FAIL), f"contains {needle}"
    if "exists" in assertion:
        want = bool(assertion["exists"])
        if value is _MISSING:
            return RuleResult.UNKNOWN, f"exists={want}"
        present = value is not None
        return (RuleResult.PASS if present == want else RuleResult.FAIL), f"exists={want}"
    if "not_exists" in assertion:
        want = bool(assertion["not_exists"])
        if value is _MISSING:
            return RuleResult.UNKNOWN, f"not_exists={want}"
        absent = value is None
        return (RuleResult.PASS if absent == want else RuleResult.FAIL), f"not_exists={want}"
    if "greater_than" in assertion:
        threshold = assertion["greater_than"]
        if value is _MISSING or not isinstance(value, (int, float)):
            return RuleResult.UNKNOWN, f">{threshold}"
        return (RuleResult.PASS if value > threshold else RuleResult.FAIL), f">{threshold}"
    if "less_than" in assertion:
        threshold = assertion["less_than"]
        if value is _MISSING or not isinstance(value, (int, float)):
            return RuleResult.UNKNOWN, f"<{threshold}"
        return (RuleResult.PASS if value < threshold else RuleResult.FAIL), f"<{threshold}"
    if "count_equals" in assertion:
        threshold = assertion["count_equals"]
        count = len(value) if isinstance(value, (list, dict)) else (value if isinstance(value, int) else _MISSING)
        if count is _MISSING:
            return RuleResult.UNKNOWN, f"count=={threshold}"
        return (RuleResult.PASS if count == threshold else RuleResult.FAIL), f"count=={threshold}"
    if "count_greater_than" in assertion:
        threshold = assertion["count_greater_than"]
        count = len(value) if isinstance(value, (list, dict)) else (value if isinstance(value, int) else _MISSING)
        if count is _MISSING:
            return RuleResult.UNKNOWN, f"count>{threshold}"
        return (RuleResult.PASS if count > threshold else RuleResult.FAIL), f"count>{threshold}"
    return RuleResult.ERROR, "unsupported-operator"


def _evaluate_rule(rule: Rule, view: EvidenceView, params: dict[str, Any]) -> tuple[RuleResult, Any, Any]:
    """Return (result, expected, actual)."""
    ev = rule.evidence
    assertion = rule.assertion

    # Relationship-existence rules.
    if "relationship_exists" in assertion:
        types = assertion["relationship_exists"]
        types = types if isinstance(types, list) else [types]
        exists = len(view.relationships(types)) > 0
        expected = f"relationship in {types}"
        if exists:
            return RuleResult.PASS, expected, exists
        # Absence is only meaningful once collection has run; otherwise UNKNOWN.
        if not view.has_collected_evidence():
            return RuleResult.UNKNOWN, expected, exists
        return RuleResult.FAIL, expected, exists

    # Related-resource matching rules.
    if "any_related_resource_matches" in assertion or "all_related_resources_match" in assertion:
        spec = assertion.get("any_related_resource_matches") or assertion.get("all_related_resources_match")
        require_all = "all_related_resources_match" in assertion
        rel_types = spec.get("relationship_types") or ([spec["relationship_type"]] if spec.get("relationship_type") else [])
        docs = view.related_resource_docs(rel_types)
        if not docs:
            return RuleResult.UNKNOWN, spec, "no related resources"
        sub_assertion = {k: v for k, v in spec.items() if k not in ("relationship_types", "relationship_type", "path")}
        path = spec.get("path", "")
        results = []
        actuals = []
        for doc in docs:
            value = _resolve_path(doc, path) if path else doc
            res, _exp = _apply_operator(sub_assertion, value, params)
            results.append(res)
            actuals.append(value if value is not _MISSING else None)
        if require_all:
            if any(r == RuleResult.FAIL for r in results):
                final = RuleResult.FAIL
            elif all(r == RuleResult.PASS for r in results):
                final = RuleResult.PASS
            else:
                final = RuleResult.UNKNOWN
        else:
            if any(r == RuleResult.PASS for r in results):
                final = RuleResult.PASS
            elif all(r == RuleResult.UNKNOWN for r in results):
                final = RuleResult.UNKNOWN
            else:
                final = RuleResult.FAIL
        return final, spec.get("path", spec), actuals

    # Scalar evidence-path rules.
    path = ev.get("path")
    if not path:
        return RuleResult.ERROR, "no-evidence-path", None
    value = view.get(path)
    result, expected = _apply_operator(assertion, value, params)
    actual = None if value is _MISSING else value
    return result, expected, actual


def _active_exception(standard: Standard, resource_id: str, rule_id: str) -> Optional[dict[str, Any]]:
    today = utcnow()[:10]
    for exc in standard.exceptions:
        if exc.get("resource_id") != resource_id:
            continue
        if rule_id not in (exc.get("rule_ids") or []):
            continue
        expires = exc.get("expires_on")
        if expires and str(expires) < today:
            continue  # expired exceptions do not apply
        return exc
    return None


def evaluate(db: Database, snapshot_id: str, standard: Standard) -> list[Finding]:
    """Evaluate every rule against every applicable Foundry. No Azure calls."""
    evidence_rows = db.list_evidence(snapshot_id)
    evidence_by_resource: dict[str, dict[str, dict[str, Any]]] = {}
    status_by_resource: dict[str, dict[str, str]] = {}
    for row in evidence_rows:
        evidence_by_resource.setdefault(row["resource_id"], {})[row["collector"]] = row["fact"]
        status_by_resource.setdefault(row["resource_id"], {})[row["collector"]] = row["collection_status"]

    rels_from: dict[str, list[dict[str, Any]]] = {}
    for rel in db.list_relationships(snapshot_id):
        rels_from.setdefault(rel["source_id"], []).append(dict(rel))

    foundry_classifications = {
        "foundry-current",
        "foundry-classic-hub",
        "azure-openai-account",
        "ai-services-account",
        "unknown-cognitive-account",
    }
    foundries = db.list_resources(snapshot_id, classifications=sorted(foundry_classifications))

    findings: list[Finding] = []
    for res in foundries:
        classification = res["classification"]
        view = EvidenceView(res["resource_id"], evidence_by_resource, status_by_resource, rels_from)
        for rule in standard.rules:
            if rule.applies_to and classification not in rule.applies_to:
                findings.append(
                    _finding(res, rule, standard, RuleResult.NOT_APPLICABLE, rule.assertion, None)
                )
                continue
            try:
                result, expected, actual = _evaluate_rule(rule, view, standard.parameters)
            except Exception as exc:  # noqa: BLE001
                result, expected, actual = RuleResult.ERROR, str(exc), None
            finding = _finding(res, rule, standard, result, expected, actual)
            findings.append(finding)
    return findings


def _finding(res, rule: Rule, standard: Standard, result: RuleResult, expected: Any, actual: Any) -> Finding:
    collection_status = "SUCCEEDED" if result != RuleResult.UNKNOWN else "UNKNOWN"
    effective = EffectiveResult(result.value)
    exception_id = None
    if result == RuleResult.FAIL:
        exc = _active_exception(standard, res["resource_id"], rule.id)
        if exc is not None:
            effective = EffectiveResult.ACCEPTED_EXCEPTION
            exception_id = exc.get("id")
    explanation = _explain(rule, result)
    return Finding(
        rule_id=rule.id,
        rule_version=standard.version,
        resource_id=res["resource_id"],
        foundry_resource_id=res["resource_id"],
        result=result.value,
        effective_result=effective.value,
        severity=rule.severity,
        expected=expected,
        actual=actual,
        explanation=explanation,
        recommended_investigation=rule.recommended_investigation,
        collection_status=collection_status,
    )


def _explain(rule: Rule, result: RuleResult) -> str:
    if result == RuleResult.PASS:
        return f"{rule.title}: evidence demonstrates adherence."
    if result == RuleResult.FAIL:
        return f"{rule.title}: evidence demonstrates non-adherence."
    if result == RuleResult.UNKNOWN:
        return f"{rule.title}: required evidence could not be collected or was insufficient."
    if result == RuleResult.NOT_APPLICABLE:
        return f"{rule.title}: not applicable to this resource classification."
    return f"{rule.title}: evaluation error."
