"""Deterministic report generation (no LLM required).

Produces stable machine-readable (CSV/JSON) and human-readable (Markdown)
reports. Output ordering is deterministic so reports diff cleanly across runs.
Reports separate facts, compliance, unknowns and migration effort, and never
contain secret values.
"""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .database import Database
from .evidence import atomic_write, utcnow

_TRANSITIONAL_RULE = "FND-AUTH-004"


def _write_csv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(["" if v is None else v for v in row])
    atomic_write(path, buffer.getvalue())


def _json_default(value: Any) -> Any:
    return value


def generate_reports(
    db: Database,
    assessment_id: str,
    snapshot_id: str,
    reports_dir: Path,
    standard_id: str,
    standard_version: str,
    scanner_version: str,
    scope_label: str,
) -> dict[str, str]:
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    resources = db.list_resources(snapshot_id)
    foundries = [r for r in resources if (r["classification"] or "").startswith(("foundry", "azure-openai", "ai-services", "unknown-cognitive"))]
    findings = db.list_findings(assessment_id, snapshot_id)
    efforts = db.list_effort(assessment_id, snapshot_id)
    relationships = db.list_relationships(snapshot_id)
    evidence = db.list_evidence(snapshot_id)
    subscriptions = db.list_subscriptions(snapshot_id)
    snapshot = db.latest_snapshot(assessment_id)
    tasks = db.list_tasks(assessment_id, snapshot_id)

    evidence_index: dict[str, dict[str, dict[str, Any]]] = {}
    for row in evidence:
        evidence_index.setdefault(row["resource_id"], {})[row["collector"]] = row["fact"]

    # -- compliance per foundry ------------------------------------------
    per_foundry_results: dict[str, Counter] = {}
    for f in findings:
        per_foundry_results.setdefault(f["foundry_resource_id"] or f["resource_id"], Counter())[f["effective_result"] or f["result"]] += 1

    def foundry_status(rid: str) -> str:
        counts = per_foundry_results.get(rid, Counter())
        if counts.get("FAIL", 0) > 0:
            return "FAIL"
        if counts.get("UNKNOWN", 0) > 0:
            return "UNKNOWN"
        if counts.get("PASS", 0) > 0 or counts.get("ACCEPTED_EXCEPTION", 0) > 0:
            return "PASS"
        return "NOT_ASSESSED"

    compliance_dist = Counter(foundry_status(f["resource_id"]) for f in foundries)
    effort_dist = Counter(e["band"] for e in efforts)

    task_status = Counter(t["status"] for t in tasks)

    # -- estate.json ------------------------------------------------------
    estate = {
        "assessmentId": assessment_id,
        "snapshotId": snapshot_id,
        "generatedAt": utcnow(),
        "scope": scope_label,
        "standard": {"id": standard_id, "version": standard_version},
        "scannerVersion": scanner_version,
        "subscriptions": [
            {"id": s["subscription_id"], "name": s["name"], "accessible": bool(s["accessible"]), "reason": s["reason"]}
            for s in subscriptions
        ],
        "counts": {
            "candidateFoundries": snapshot["candidate_foundries"] if snapshot else len(foundries),
            "subscriptionsAccessible": snapshot["subscriptions_accessible"] if snapshot else 0,
            "compliance": dict(compliance_dist),
            "effort": dict(effort_dist),
            "tasks": dict(task_status),
        },
        "foundries": [
            {
                "resourceId": f["resource_id"],
                "subscriptionId": f["subscription_id"],
                "resourceGroup": f["resource_group"],
                "classification": f["classification"],
                "kind": f["kind"],
                "sku": f["sku"],
                "location": f["location"],
                "complianceStatus": foundry_status(f["resource_id"]),
            }
            for f in foundries
        ],
    }
    atomic_write(reports_dir / "estate.json", json.dumps(estate, indent=2, sort_keys=True) + "\n")

    # -- foundries.csv ----------------------------------------------------
    _write_csv(
        reports_dir / "foundries.csv",
        ["resourceId", "subscriptionId", "resourceGroup", "classification", "kind", "sku", "location",
         "projectCount", "modelDeploymentCount", "complianceStatus"],
        [
            [
                f["resource_id"], f["subscription_id"], f["resource_group"], f["classification"],
                f["kind"], f["sku"], f["location"],
                (evidence_index.get(f["resource_id"], {}).get("projects", {}) or {}).get("count", ""),
                (evidence_index.get(f["resource_id"], {}).get("model_deployments", {}) or {}).get("count", ""),
                foundry_status(f["resource_id"]),
            ]
            for f in foundries
        ],
    )

    # -- projects.csv -----------------------------------------------------
    project_rows = []
    for f in foundries:
        for proj in (evidence_index.get(f["resource_id"], {}).get("projects", {}) or {}).get("projects", []):
            project_rows.append([
                f["resource_id"], proj.get("id"), proj.get("name"),
                ";".join(proj.get("capabilityHosts", []) or []),
                proj.get("capabilityHostNetworking"),
            ])
    _write_csv(reports_dir / "projects.csv",
               ["foundryResourceId", "projectResourceId", "name", "capabilityHosts", "capabilityHostNetworking"],
               project_rows)

    # -- model-footprint.csv ---------------------------------------------
    model_rows = []
    for f in foundries:
        for dep in (evidence_index.get(f["resource_id"], {}).get("model_deployments", {}) or {}).get("deployments", []):
            model_rows.append([
                dep.get("foundryResourceId"), dep.get("projectResourceId"), dep.get("deploymentName"),
                dep.get("modelName"), dep.get("modelVersion"), dep.get("publisher"), dep.get("skuName"),
                dep.get("capacity"), dep.get("provisioningState"), dep.get("raiPolicy"), dep.get("collectionStatus"),
            ])
    _write_csv(reports_dir / "model-footprint.csv",
               ["foundryResourceId", "projectResourceId", "deploymentName", "modelName", "modelVersion",
                "publisher", "skuName", "capacity", "provisioningState", "raiPolicy", "collectionStatus"],
               model_rows)

    # -- peripheral-footprint.csv ----------------------------------------
    peripheral_rows = []
    peripheral_collectors = ("keyvault", "cosmos", "storage", "search", "apim")
    for r in resources:
        for collector in peripheral_collectors:
            fact = evidence_index.get(r["resource_id"], {}).get(collector)
            if fact is None:
                continue
            referencing = db.relationships_to(snapshot_id, r["resource_id"])
            peripheral_rows.append([
                collector, r["resource_id"],
                ";".join(sorted({rel["source_id"] for rel in referencing})),
                fact.get("publicNetworkAccess"), fact.get("hasPrivateEndpoint"),
                fact.get("totalGB") or fact.get("usedCapacityGB") or fact.get("storageGB"),
                fact.get("referencingResourceCount"),
            ])
    _write_csv(reports_dir / "peripheral-footprint.csv",
               ["resourceType", "resourceId", "connectedResources", "publicNetworkAccess",
                "hasPrivateEndpoint", "sizeGB", "referencingResourceCount"],
               peripheral_rows)

    # -- relationships.csv -----------------------------------------------
    _write_csv(reports_dir / "relationships.csv",
               ["sourceId", "targetId", "relationshipType", "evidenceType", "confidence", "collectedAt"],
               [[r["source_id"], r["target_id"], r["relationship_type"], r["evidence_type"], r["confidence"], r["collected_at"]]
                for r in relationships])

    # -- findings.csv -----------------------------------------------------
    _write_csv(reports_dir / "findings.csv",
               ["foundryResourceId", "resourceId", "ruleId", "ruleVersion", "result", "effectiveResult",
                "severity", "expected", "actual", "collectionStatus", "exceptionId", "explanation"],
               [[f["foundry_resource_id"], f["resource_id"], f["rule_id"], f["rule_version"], f["result"],
                 f["effective_result"], f["severity"], f["expected"], f["actual"], f["collection_status"],
                 f["exception_id"], f["explanation"]]
                for f in findings])

    # -- migration-effort.csv --------------------------------------------
    _write_csv(reports_dir / "migration-effort.csv",
               ["foundryResourceId", "band", "confidence", "dataGB", "drivers", "unknownDependencies"],
               [[e["foundry_resource_id"], e["band"], e["confidence"], e["data_gb"],
                 "; ".join(json.loads(e["drivers"])), "; ".join(json.loads(e["unknown_dependencies"]))]
                for e in efforts])

    # -- unknowns.csv -----------------------------------------------------
    unknown_rows = []
    for f in findings:
        if (f["effective_result"] or f["result"]) == "UNKNOWN":
            unknown_rows.append([f["foundry_resource_id"], f["rule_id"], f["severity"], f["recommended_investigation"] or f["explanation"]])
    for s in subscriptions:
        if not s["accessible"]:
            unknown_rows.append([s["subscription_id"], "SUBSCRIPTION_INACCESSIBLE", "info", s["reason"]])
    for t in tasks:
        if t["status"] in ("BLOCKED_PERMISSION", "BLOCKED_NETWORK", "UNSUPPORTED", "FAILED"):
            unknown_rows.append([t["resource_id"], f"TASK_{t['collector']}_{t['status']}", "info", t["last_error"] or ""])
    _write_csv(reports_dir / "unknowns.csv",
               ["resourceId", "issue", "severity", "detail"], unknown_rows)

    # -- executive summary (markdown) ------------------------------------
    md = _executive_markdown(
        assessment_id, snapshot_id, scope_label, standard_id, standard_version, scanner_version,
        subscriptions, foundries, compliance_dist, effort_dist, task_status, findings, efforts, foundry_status,
    )
    atomic_write(reports_dir / "executive-summary.md", md)

    return {
        "reports_dir": str(reports_dir),
        "executive_summary": str(reports_dir / "executive-summary.md"),
    }


def _executive_markdown(
    assessment_id, snapshot_id, scope_label, standard_id, standard_version, scanner_version,
    subscriptions, foundries, compliance_dist, effort_dist, task_status, findings, efforts, foundry_status,
) -> str:
    accessible = [s for s in subscriptions if s["accessible"]]
    inaccessible = [s for s in subscriptions if not s["accessible"]]
    lines: list[str] = []
    lines.append("# Foundry Estate Assessment — Executive Summary")
    lines.append("")
    lines.append(f"- Generated: {utcnow()}")
    lines.append(f"- Scope: `{scope_label}`")
    if scope_label.startswith("all-accessible"):
        lines.append("  - This is **all subscriptions accessible to the current identity**, not a guaranteed tenant-wide view.")
    lines.append(f"- Standard: `{standard_id}` {standard_version}")
    lines.append(f"- Scanner version: {scanner_version}")
    lines.append(f"- Assessment id: `{assessment_id}`")
    lines.append("")
    lines.append("## Scope coverage")
    lines.append("")
    lines.append(f"- Subscriptions accessible: {len(accessible)}")
    lines.append(f"- Subscriptions inaccessible: {len(inaccessible)}")
    lines.append(f"- Foundries discovered: {len(foundries)}")
    lines.append("")
    lines.append("## Assessment progress")
    lines.append("")
    for status in sorted(task_status):
        lines.append(f"- {status}: {task_status[status]}")
    lines.append("")
    lines.append("## Pattern adherence (per Foundry)")
    lines.append("")
    for key in ("PASS", "FAIL", "UNKNOWN", "NOT_ASSESSED"):
        if compliance_dist.get(key):
            lines.append(f"- {key}: {compliance_dist[key]}")
    lines.append("")
    lines.append("## Migration effort distribution")
    lines.append("")
    for band in ("S", "M", "L", "XL", "UNKNOWN"):
        if effort_dist.get(band):
            lines.append(f"- {band}: {effort_dist[band]}")
    lines.append("")

    # Transitional pattern callout.
    transitional = [f for f in findings if f["rule_id"] == _TRANSITIONAL_RULE and (f["effective_result"] or f["result"]) in ("PASS", "ACCEPTED_EXCEPTION", "FAIL")]
    if transitional:
        lines.append("## Accepted transitional patterns")
        lines.append("")
        lines.append("Team-to-APIM API-key authentication is recorded as an **accepted transitional pattern**, "
                     "not an unqualified security best practice.")
        lines.append("")

    # Systemic findings: most common FAIL rules.
    fail_counter = Counter(f["rule_id"] for f in findings if (f["effective_result"] or f["result"]) == "FAIL")
    if fail_counter:
        lines.append("## Major systemic findings")
        lines.append("")
        for rule_id, count in fail_counter.most_common(10):
            lines.append(f"- `{rule_id}`: {count} Foundries")
        lines.append("")

    unknown_counter = Counter(f["rule_id"] for f in findings if (f["effective_result"] or f["result"]) == "UNKNOWN")
    if unknown_counter:
        lines.append("## Major unknowns")
        lines.append("")
        for rule_id, count in unknown_counter.most_common(10):
            lines.append(f"- `{rule_id}`: {count} Foundries (insufficient evidence — see `unknowns.csv`)")
        lines.append("")

    # Largest migration footprints.
    ranked = sorted(efforts, key=lambda e: e["data_gb"], reverse=True)[:5]
    if ranked:
        lines.append("## Largest migration footprints")
        lines.append("")
        for e in ranked:
            lines.append(f"- `{e['foundry_resource_id']}` — {e['band']} ({e['data_gb']} GB, confidence {e['confidence']})")
        lines.append("")

    lines.append("## Report files")
    lines.append("")
    lines.append("Machine-readable outputs (stable schemas) are in this directory: "
                 "`estate.json`, `foundries.csv`, `projects.csv`, `model-footprint.csv`, "
                 "`peripheral-footprint.csv`, `relationships.csv`, `findings.csv`, "
                 "`migration-effort.csv`, `unknowns.csv`.")
    lines.append("")
    return "\n".join(lines)
