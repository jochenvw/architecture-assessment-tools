"""Deterministic migration / upgrade effort sizing.

Effort is derived from configurable drivers (architecture generation, project
and deployment counts, data footprint, shared dependencies, networking and
identity complexity, and unknown evidence) -- never from the count of failed
rules. Every estimate lists the drivers that produced it. Compliance status,
migration effort, data footprint and confidence are kept independent.
"""

from __future__ import annotations

from typing import Any

from .database import Database
from .models import Confidence, EffortBand

# Default scoring weights and band thresholds; overridable via standard.effort.
_DEFAULTS: dict[str, Any] = {
    "weights": {
        "classic_hub": 40,
        "per_project": 4,
        "per_deployment": 1,
        "data_gb_per_100": 6,
        "per_search_index_10": 3,
        "shared_dependency": 8,
        "cross_subscription_dependency": 6,
        "networking_unknown": 4,
        "private_endpoint_missing": 6,
    },
    "bands": {"S": 10, "M": 30, "L": 60},  # <=S small, <=M, <=L, else XL
}


def _cfg(standard_effort: dict[str, Any]) -> dict[str, Any]:
    cfg = {"weights": dict(_DEFAULTS["weights"]), "bands": dict(_DEFAULTS["bands"])}
    if standard_effort:
        cfg["weights"].update(standard_effort.get("weights", {}) or {})
        cfg["bands"].update(standard_effort.get("bands", {}) or {})
    return cfg


def _band(score: float, bands: dict[str, Any]) -> EffortBand:
    if score <= bands["S"]:
        return EffortBand.S
    if score <= bands["M"]:
        return EffortBand.M
    if score <= bands["L"]:
        return EffortBand.L
    return EffortBand.XL


def estimate_for_foundry(
    db: Database,
    snapshot_id: str,
    foundry_id: str,
    classification: str,
    standard_effort: dict[str, Any],
) -> dict[str, Any]:
    cfg = _cfg(standard_effort)
    w = cfg["weights"]
    drivers: list[str] = []
    unknown_deps: list[str] = []
    score = 0.0

    def fact(collector: str) -> dict[str, Any]:
        ev = db.get_evidence(snapshot_id, foundry_id, collector)
        return ev["fact"] if ev else {}

    if classification == "foundry-classic-hub":
        score += w["classic_hub"]
        drivers.append("classic hub-based architecture")

    projects = fact("projects").get("count") or 0
    if projects:
        score += projects * w["per_project"]
        drivers.append(f"{projects} projects")

    deployments = fact("model_deployments").get("count") or 0
    if deployments:
        score += deployments * w["per_deployment"]
        drivers.append(f"{deployments} model deployments")

    net = fact("networking")
    if net.get("hubSpokePeering") == "unknown" or net.get("privateDnsAssociation") == "unknown":
        score += w["networking_unknown"]
        unknown_deps.append("network topology / DNS evidence incomplete")
    if net and net.get("foundryPrivateEndpointPresent") is False:
        score += w["private_endpoint_missing"]
        drivers.append("Foundry lacks an approved private endpoint")

    # Peripheral footprint via proven relationships.
    data_gb = 0.0
    cross_subs = set()
    foundry_sub = foundry_id.split("/")[2] if "/subscriptions/" in foundry_id else None
    rel_types = {
        "PROJECT_USES_KEYVAULT": "keyvault",
        "PROJECT_USES_COSMOS": "cosmos",
        "PROJECT_USES_STORAGE": "storage",
        "PROJECT_USES_SEARCH": "search",
    }
    project_ids = {
        r["target_id"]
        for r in db.relationships_from(snapshot_id, foundry_id)
        if r["relationship_type"] == "FOUNDRY_HAS_PROJECT"
    }
    sources = {foundry_id} | project_ids
    peripheral_targets: dict[str, str] = {}
    for source in sources:
        for rel in db.relationships_from(snapshot_id, source):
            collector = rel_types.get(rel["relationship_type"])
            if collector:
                peripheral_targets[rel["target_id"]] = collector

    for target_id, collector in sorted(peripheral_targets.items()):
        ev = db.get_evidence(snapshot_id, target_id, collector)
        pf = ev["fact"] if ev else {}
        if not ev:
            unknown_deps.append(f"{collector} footprint unavailable for {target_id}")
            continue
        for key in ("totalGB", "usedCapacityGB", "storageGB"):
            if isinstance(pf.get(key), (int, float)):
                data_gb += float(pf[key])
        if collector == "search" and isinstance(pf.get("indexCount"), int):
            score += (pf["indexCount"] / 10.0) * w["per_search_index_10"]
            if pf["indexCount"]:
                drivers.append(f"{pf['indexCount']} Search indexes")
        if (pf.get("referencingResourceCount") or 0) > 1:
            score += w["shared_dependency"]
            drivers.append(f"shared {collector} dependency")
        target_sub = target_id.split("/")[2] if "/subscriptions/" in target_id else None
        if target_sub and foundry_sub and target_sub != foundry_sub:
            cross_subs.add(target_sub)

    if data_gb:
        score += (data_gb / 100.0) * w["data_gb_per_100"]
        drivers.append(f"{round(data_gb, 1)} GB data footprint")
    if cross_subs:
        score += len(cross_subs) * w["cross_subscription_dependency"]
        drivers.append("cross-subscription dependencies")

    # Confidence reflects how much evidence was unavailable.
    if not fact("foundry"):
        confidence = Confidence.LOW
        band = EffortBand.UNKNOWN
    elif len(unknown_deps) >= 3:
        confidence = Confidence.LOW
        band = _band(score, cfg["bands"])
    elif unknown_deps:
        confidence = Confidence.MEDIUM
        band = _band(score, cfg["bands"])
    else:
        confidence = Confidence.HIGH
        band = _band(score, cfg["bands"])

    if not drivers:
        drivers.append("configuration-only recreation")

    return {
        "foundry_resource_id": foundry_id,
        "band": band.value,
        "confidence": confidence.value,
        "drivers": drivers,
        "data_gb": round(data_gb, 2),
        "unknown_dependencies": unknown_deps,
    }


def estimate_all(db: Database, snapshot_id: str, standard_effort: dict[str, Any]) -> list[dict[str, Any]]:
    foundries = db.list_resources(
        snapshot_id,
        classifications=[
            "foundry-current",
            "foundry-classic-hub",
            "azure-openai-account",
            "ai-services-account",
            "unknown-cognitive-account",
        ],
    )
    return [
        estimate_for_foundry(db, snapshot_id, f["resource_id"], f["classification"], standard_effort)
        for f in foundries
    ]
