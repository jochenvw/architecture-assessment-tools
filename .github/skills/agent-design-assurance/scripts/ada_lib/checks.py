"""Quality gates for a discovery package (goal: evidence-first, honest unknowns).

Each gate yields ``Issue(level, code, message)``. ``error`` blocks packaging;
``warning`` must be reviewed by a human. Gates are deliberately mechanical:
they verify structure, traceability and scoring discipline, not the quality
of the architectural judgement itself.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import profiles, render, sanitize, workspace
from .jsonschema_lite import load_schema, validate
from .paths import AUTHORED_MARKDOWN, DOMAIN_TITLES, JSON_FILES, REQUIRED_FILES, SCHEMAS_DIR, WORK_DIR_NAME
from .util import load_json


@dataclass
class Issue:
    level: str  # error | warning | info
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level.upper():7}] {self.code}: {self.message}"


ROADMAP = re.compile(
    r"(?i)\b(internal roadmap|on the roadmap|roadmap item|coming soon|will (?:be )?(?:released|shipped|launched|generally available)|"
    r"planned (?:release|GA)|expected (?:GA|release) (?:in|by)|private preview|under NDA)\b"
)
PLACEHOLDER = re.compile(r"\{\{[^}]*\}\}")
ROLE_NAMES = re.compile(r"(?i)^(development team|business owner|platform owner|security owner|operations owner|data owner|product owner|tech(?:nical)? lead|architect|unassigned|tbd)$")


class Context:
    def __init__(self, out: Path):
        self.out = Path(out)
        self.docs: dict[str, Any] = {}
        self.issues: list[Issue] = []

    def add(self, level: str, code: str, message: str) -> None:
        self.issues.append(Issue(level, code, message))

    def doc(self, name: str) -> Any:
        return self.docs.get(name) or {}


def _files_and_schemas(ctx: Context) -> None:
    for name in REQUIRED_FILES:
        if not (ctx.out / name).exists():
            ctx.add("error", "missing-file", f"{name} is missing (run `ada.py render` for generated files).")
    for name, schema_name in JSON_FILES.items():
        path = ctx.out / name
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            ctx.add("error", "invalid-json", f"{name}: {exc}")
            continue
        ctx.docs[name] = data
        for err in validate(data, load_schema(SCHEMAS_DIR / schema_name))[:25]:
            ctx.add("error", "schema", f"{name}: {err}")


def _dupes(ctx: Context, label: str, ids: list[str]) -> None:
    for value, count in Counter(ids).items():
        if count > 1:
            ctx.add("error", "duplicate-id", f"{label} id {value} appears {count} times.")


def _ids(items: list[dict[str, Any]]) -> list[str]:
    return [i.get("id") for i in items if isinstance(i, dict) and i.get("id")]


def _references(ctx: Context) -> tuple[dict[str, Any], dict[str, Any]]:
    evidence = {e["id"]: e for e in ctx.doc("evidence.json").get("evidence", []) if isinstance(e, dict) and "id" in e}
    assessment = ctx.doc("assessment.json")
    criteria = {c["id"]: c for c in assessment.get("criteria", []) if isinstance(c, dict) and "id" in c}
    arch = ctx.doc("architecture.json")
    entities = {e["id"]: e for e in arch.get("entities", []) if isinstance(e, dict) and "id" in e}

    _dupes(ctx, "evidence", _ids(ctx.doc("evidence.json").get("evidence", [])))
    _dupes(ctx, "criterion", _ids(assessment.get("criteria", [])))
    _dupes(ctx, "observation", _ids(assessment.get("observations", [])))
    _dupes(ctx, "question", _ids(assessment.get("open_questions", [])))
    _dupes(ctx, "entity", _ids(arch.get("entities", [])))
    _dupes(ctx, "relationship", _ids(arch.get("relationships", [])))
    _dupes(ctx, "flow", _ids(ctx.doc("execution-flows.json").get("flows", [])))
    _dupes(ctx, "technology", _ids(ctx.doc("technology-inventory.json").get("items", [])))
    _dupes(ctx, "workload characteristic", _ids(ctx.doc("workload-characteristics.json").get("characteristics", [])))
    _dupes(ctx, "design decision", _ids(ctx.doc("design-decisions.json").get("decisions", [])))

    def check_ev(where: str, refs: list[str] | None) -> None:
        for ref in refs or []:
            if ref not in evidence:
                ctx.add("error", "unresolved-evidence", f"{where} references unknown evidence {ref}.")

    def check_crit(where: str, refs: list[str] | None) -> None:
        for ref in refs or []:
            if ref not in criteria:
                ctx.add("error", "unresolved-criterion", f"{where} references unknown criterion {ref}.")

    def check_ent(where: str, ref: str | None) -> None:
        if ref and ref not in entities:
            ctx.add("error", "unresolved-entity", f"{where} references unknown entity {ref}.")

    for ev in evidence.values():
        check_crit(ev["id"], ev.get("criteria"))
    for c in criteria.values():
        check_ev(c["id"], c.get("evidence_refs"))
        check_ev(c["id"] + " (validation)", c.get("validation_evidence_refs"))
    for o in assessment.get("observations", []):
        check_ev(o.get("id", "observation"), o.get("evidence_refs"))
        check_crit(o.get("id", "observation"), o.get("criteria"))
    for q in assessment.get("open_questions", []):
        check_ev(q.get("id", "question"), q.get("evidence_refs"))
        check_crit(q.get("id", "question"), q.get("criteria"))
        if not q.get("criteria") and not q.get("evidence_refs"):
            ctx.add("error", "question-unanchored", f"{q.get('id')} has neither criteria nor evidence references.")
    for e in entities.values():
        check_ev(e["id"], e.get("evidence_refs"))
        check_ent(e["id"] + ".parent", e.get("parent"))
    for r in arch.get("relationships", []):
        check_ev(r["id"], r.get("evidence_refs"))
        for key in ("source", "target", "identity"):
            check_ent(f"{r['id']}.{key}", r.get(key))
    for flow in ctx.doc("execution-flows.json").get("flows", []):
        check_ev(flow["id"], flow.get("evidence_refs"))
        check_ent(flow["id"] + ".entry_point", flow.get("entry_point"))
        step_ids = [s["id"] for s in flow.get("steps", [])]
        _dupes(ctx, f"{flow['id']} step", step_ids)
        for s in flow.get("steps", []):
            where = f"{flow['id']}.{s['id']}"
            check_ev(where, s.get("evidence_refs"))
            check_ent(where + ".actor", s.get("actor"))
            check_ent(where + ".target", s.get("target"))
            for nxt in (s.get("next") or []) + ([s["on_failure"]] if s.get("on_failure") else []):
                if nxt not in step_ids:
                    ctx.add("error", "unresolved-step", f"{where} points to unknown step {nxt}.")
    for t in ctx.doc("technology-inventory.json").get("items", []):
        check_ev(t["id"], t.get("evidence_refs"))
    for w in ctx.doc("workload-characteristics.json").get("characteristics", []):
        check_ev(w["id"], w.get("evidence_refs"))
    for d in ctx.doc("design-decisions.json").get("decisions", []):
        check_ev(d["id"], d.get("evidence_refs"))
        check_crit(d["id"], d.get("criteria"))
        if d.get("rationale") and not d.get("rationale_documented") and d.get("status") != "documented":
            ctx.add("warning", "rationale-invented", f"{d['id']} has a rationale but rationale_documented is false; do not invent rationale.")
    azure_aliases = {r["alias"] for r in ctx.doc("azure-configuration.json").get("resources", [])}
    for r in ctx.doc("azure-configuration.json").get("resources", []):
        check_ev(r["alias"], r.get("evidence_ids"))
    for e in entities.values():
        if e.get("azure_alias") and azure_aliases and e["azure_alias"] not in azure_aliases:
            ctx.add("warning", "alias-not-collected", f"{e['id']} uses {e['azure_alias']} which is not in azure-configuration.json.")
    return evidence, criteria


def _expected_criteria(ctx: Context, criteria: dict[str, Any]) -> None:
    assessment = ctx.doc("assessment.json")
    resolved_path = ctx.out / WORK_DIR_NAME / "resolved-criteria.json"
    try:
        if resolved_path.exists():
            expected = {c["id"] for c in load_json(resolved_path)["criteria"]}
        else:
            expected = {c.id for c in profiles.resolve(list(assessment.get("profiles", []))).criteria}
    except (profiles.ProfileError, KeyError, ValueError) as exc:
        ctx.add("warning", "profiles-unresolvable", f"Could not resolve selected profiles to verify completeness: {exc}")
        return
    for cid in sorted(expected - set(criteria)):
        ctx.add("error", "criterion-missing", f"Criterion {cid} from the selected profiles has no assessment entry.")
    for cid in sorted(set(criteria) - expected):
        ctx.add("error", "criterion-unexpected", f"Criterion {cid} is not part of the selected profiles.")
    manifest_profiles = [p.get("id") for p in ctx.doc("manifest.json").get("profiles", [])]
    if manifest_profiles and manifest_profiles != list(assessment.get("profiles", [])):
        ctx.add("error", "profile-mismatch", "manifest.json profiles differ from assessment.json profiles.")


def _scoring(ctx: Context, evidence: dict[str, Any], criteria: dict[str, Any], allow_incomplete: bool) -> None:
    for c in criteria.values():
        cid, m, st, conf, cov = c["id"], c["maturity"], c["status"], c["confidence"], c["discovery_coverage"]
        refs = c.get("evidence_refs") or []
        if cov == "not_investigated":
            ctx.add("warning" if allow_incomplete else "error", "not-investigated", f"{cid} has not been investigated.")
            continue
        if c["applicability"] == "not_applicable" or st == "not_applicable" or m == "N/A":
            if not (c["applicability"] == "not_applicable" and st == "not_applicable" and m == "N/A"):
                ctx.add("error", "na-inconsistent", f"{cid}: applicability, status and maturity must all be not applicable together.")
            if not (c.get("applicability_justification") or "").strip():
                ctx.add("error", "na-unjustified", f"{cid} is not applicable without applicability_justification.")
            continue
        if st == "unknown" and m != "U":
            ctx.add("error", "unknown-scored", f"{cid}: status unknown must be maturity U (unknown is not 0).")
        if m == "U":
            if not (c.get("discovery_attempts") or []):
                ctx.add("error", "unknown-without-attempts", f"{cid}: maturity U requires discovery_attempts describing where evidence was sought.")
            if st in ("observed", "documented") and not (c.get("unknowns") or []):
                ctx.add("warning", "unknown-unexplained", f"{cid}: status {st} but maturity U; record why in unknowns.")
        if conf == "none" and m not in ("U", "N/A"):
            ctx.add("error", "score-without-confidence", f"{cid}: confidence none cannot support maturity {m}.")
        if m.isdigit():
            if not refs:
                ctx.add("error", "score-without-evidence", f"{cid}: maturity {m} requires evidence_refs.")
            if m == "0":
                absence = [r for r in refs if evidence.get(r, {}).get("confirms_absence")]
                if not c.get("absence_confirmed") or st != "observed" or not absence:
                    ctx.add("error", "zero-without-absence",
                            f"{cid}: maturity 0 requires absence_confirmed, status observed and evidence with confirms_absence (missing information is U, not 0).")
            if m == "5" and not (c.get("validation_evidence_refs") or []):
                ctx.add("error", "five-without-validation", f"{cid}: maturity 5 requires validation_evidence_refs.")
            if st == "inferred" and int(m) >= 4:
                ctx.add("warning", "inferred-high-maturity", f"{cid}: maturity {m} rests on inferred evidence.")
        if c.get("absence_confirmed") and not any(evidence.get(r, {}).get("confirms_absence") for r in refs):
            ctx.add("error", "absence-unsupported", f"{cid}: absence_confirmed needs evidence with confirms_absence true.")
        if st == "inferred" and conf == "high":
            ctx.add("warning", "inferred-high-confidence", f"{cid}: inferred status with high confidence.")
        if st == "conflicting" and not (c.get("conflicting_evidence") or []):
            ctx.add("error", "conflict-undescribed", f"{cid}: status conflicting requires conflicting_evidence.")
        if st in ("observed", "documented", "inferred") and not refs:
            ctx.add("error", "status-without-evidence", f"{cid}: status {st} requires evidence_refs.")
        if st == "observed" and refs and not any(evidence.get(r, {}).get("classification") == "observed" for r in refs):
            ctx.add("warning", "observed-without-observed-evidence", f"{cid}: status observed but no referenced evidence is classified observed.")
        if cov in ("attempted", "partial") and not (c.get("discovery_attempts") or []):
            ctx.add("error", "coverage-without-attempts", f"{cid}: coverage {cov} requires discovery_attempts.")
        if c.get("emphasis") in ("high", "critical") and m == "U":
            asked = any(cid in q.get("criteria", []) for q in ctx.doc("assessment.json").get("open_questions", []))
            if not asked and not (c.get("follow_up_questions") or []):
                ctx.add("warning", "emphasis-unknown-unasked", f"{cid} ({c['emphasis']}) is unknown and has no follow-up question.")

    for dom in DOMAIN_TITLES:
        items = [c for c in criteria.values() if c["domain"] == dom]
        if items and all(c["discovery_coverage"] == "not_investigated" for c in items):
            ctx.add("warning" if allow_incomplete else "error", "domain-skipped", f"Domain {dom} ({DOMAIN_TITLES[dom]}) was not investigated.")

    used = set()
    for c in criteria.values():
        used.update(c.get("evidence_refs") or [])
        used.update(c.get("validation_evidence_refs") or [])
    for o in ctx.doc("assessment.json").get("observations", []):
        used.update(o.get("evidence_refs") or [])
    for ev in evidence.values():
        if not ev.get("criteria") and ev["id"] not in used:
            ctx.add("warning", "evidence-orphan", f"{ev['id']} is not linked to any criterion or observation.")


def _observations(ctx: Context) -> None:
    obs = ctx.doc("assessment.json").get("observations", [])
    if obs and not any(o.get("nature") == "strength" or o.get("category") == "retain" for o in obs):
        ctx.add("warning", "no-strengths", "No strengths/retain observations recorded; capture what works well.")
    criteria = ctx.doc("assessment.json").get("criteria", [])
    if criteria and not obs and any(c.get("discovery_coverage") != "not_investigated" for c in criteria):
        ctx.add("warning", "no-observations", "No preliminary observations recorded.")
    for o in obs:
        if o.get("validation_status") == "unvalidated":
            for key in ("owner", "target_date"):
                if o.get(key) and not ROLE_NAMES.match(str(o[key])):
                    ctx.add("warning", "unagreed-assignment", f"{o['id']}: {key} set on an unvalidated observation; only record if explicitly documented.")
        if o.get("nature") == "potential_gap" and not (o.get("improvement_options") or o.get("follow_up_question")):
            ctx.add("warning", "gap-not-constructive", f"{o['id']}: potential gap without improvement options or follow-up question.")
        if o.get("confidence") == "none" and o.get("risk_severity") not in ("not_assessed", "informational"):
            ctx.add("warning", "severity-without-confidence", f"{o['id']}: risk severity assigned with confidence none.")


def _manifest(ctx: Context, evidence: dict[str, Any]) -> None:
    m = ctx.doc("manifest.json")
    if not m:
        return
    modes = set(m.get("discovery_modes", []))
    scope = m.get("azure_scope", {})
    kinds = Counter(e["source_type"] for e in evidence.values())
    if any(k in kinds for k in ("azure_resource_config", "azure_policy", "azure_rbac")) and "azure_configuration" not in modes:
        ctx.add("error", "azure-mode-undeclared", "Azure configuration evidence present but discovery_modes lacks azure_configuration.")
    if "azure_configuration" in modes and not (scope.get("authorised") and scope.get("authorised_by")):
        ctx.add("error", "azure-unauthorised", "azure_configuration mode requires azure_scope.authorised and authorised_by.")
    if kinds.get("telemetry_aggregate") and not ("azure_telemetry" in modes and scope.get("telemetry_authorised")):
        ctx.add("error", "telemetry-unauthorised", "Telemetry evidence requires azure_telemetry mode and telemetry_authorised.")
    if not m.get("evidence_sources_inspected"):
        ctx.add("warning", "sources-unrecorded", "manifest.evidence_sources_inspected is empty.")
    if not m.get("limitations"):
        ctx.add("warning", "limitations-unrecorded", "manifest.limitations is empty; record known limitations explicitly.")
    for ev in evidence.values():
        if ev.get("perspective") == "deployed" and not ev["source_type"].startswith("azure_") and ev["classification"] == "observed":
            ctx.add("warning", "deployed-without-azure", f"{ev['id']}: deployed perspective classified observed without Azure evidence.")
        if ev.get("perspective") == "runtime" and ev["source_type"] not in ("telemetry_aggregate", "evaluation_result", "interview", "documentation"):
            ctx.add("warning", "runtime-source", f"{ev['id']}: runtime perspective from source_type {ev['source_type']}.")


def _markdown(ctx: Context) -> None:
    for name in AUTHORED_MARKDOWN + ["open-questions.md"]:
        path = ctx.out / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            if PLACEHOLDER.search(line):
                ctx.add("error", "template-placeholder", f"{name}:{i} still contains a template placeholder.")
                break
        for i, line in enumerate(text.splitlines(), start=1):
            if ROADMAP.search(line):
                ctx.add("warning", "roadmap-language", f"{name}:{i} looks like roadmap content; discovery must not include roadmap assumptions.")
    readme = ctx.out / "discovery-report.md"
    if readme.exists():
        text = readme.read_text(encoding="utf-8")
        for dom, title in DOMAIN_TITLES.items():
            if not re.search(rf"(?im)^#+\s.*\b{dom}\b", text):
                ctx.add("warning", "report-domain-missing", f"discovery-report.md has no heading for domain {dom} ({title}).")


def _rendered_fresh(ctx: Context) -> None:
    if not ctx.docs.get("assessment.json") or "discovery-coverage.json" not in ctx.docs:
        return
    fresh = render.coverage(ctx.docs["assessment.json"], ctx.doc("evidence.json"))
    current = dict(ctx.docs["discovery-coverage.json"])
    fresh.pop("generated_at", None)
    current.pop("generated_at", None)
    if fresh != current:
        ctx.add("error", "render-stale", "discovery-coverage.json is out of date; run `ada.py render`.")
    for name, fn in (("assessment.csv", render.assessment_csv), ("preliminary-observations.csv", render.observations_csv), ("open-questions.md", render.open_questions_md)):
        path = ctx.out / name
        if path.exists() and path.read_text(encoding="utf-8") != fn(ctx.docs["assessment.json"]):
            ctx.add("error", "render-stale", f"{name} is out of date; run `ada.py render`.")


def _information_protection(ctx: Context) -> None:
    work = ctx.out / WORK_DIR_NAME
    aliases = sanitize.AliasMap(work / "alias-map.json" if work.exists() else None)
    result, excluded = sanitize.run(workspace.package_files(ctx.out), ctx.out, aliases, work / "sanitize-allowlist.json", apply=False)
    for f in result.blocking:
        ctx.add("error", f"sensitive-{f.severity}", f"{f.file}:{f.line} {f.kind} ({f.excerpt}) - run `ada.py sanitize --apply` or rewrite/allow-list.")
    for rel in excluded:
        ctx.add("warning", "non-text-file", f"{rel} is not a text file and will be excluded from the package.")


def _integrity(ctx: Context, allow_repo_changes: bool) -> None:
    if not (ctx.out / WORK_DIR_NAME / "scope.json").exists():
        ctx.add("info", "integrity-skipped", "No workspace scope (e.g. example package); repository read-only check skipped.")
        return
    unchanged = workspace.repository_unchanged(ctx.out)
    if unchanged is None:
        ctx.add("warning", "integrity-unknown", "Git unavailable; cannot verify that the repository was not modified.")
    elif not unchanged:
        ctx.add("warning" if allow_repo_changes else "error", "repository-modified",
                "Repository working tree changed since `init`. Discovery must be read-only; investigate before packaging.")


def run(out: Path, allow_incomplete: bool = False, allow_repo_changes: bool = False, skip_sensitive: bool = False) -> list[Issue]:
    ctx = Context(out)
    _files_and_schemas(ctx)
    evidence, criteria = _references(ctx)
    _expected_criteria(ctx, criteria)
    _scoring(ctx, evidence, criteria, allow_incomplete)
    _observations(ctx)
    _manifest(ctx, evidence)
    _markdown(ctx)
    _rendered_fresh(ctx)
    if not skip_sensitive:
        _information_protection(ctx)
    _integrity(ctx, allow_repo_changes)
    return ctx.issues
