"""Foundry projects collector: enumerate projects and capability hosts."""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, ok


def _capability_host_networking(cap_host: dict[str, Any]) -> str:
    props = cap_host.get("properties") or cap_host
    # VNet injection is evidenced by a customer-supplied subnet / network settings.
    if props.get("subnetId") or props.get("vnetInjection") or props.get("networkInjections"):
        return "vnet-injected"
    if props.get("publicNetworkAccess") and str(props.get("publicNetworkAccess")).lower() == "disabled":
        return "unknown"
    return "unknown"


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(resource_id, api_versions.COGNITIVE_SERVICES_PROJECTS, sub_path="/projects")
    values = raw.get("value", []) if isinstance(raw, dict) else []
    projects = []
    for proj in values:
        proj_props = proj.get("properties") or {}
        cap_hosts = proj_props.get("capabilityHosts") or proj.get("capabilityHosts") or []
        if isinstance(cap_hosts, dict):
            cap_hosts = list(cap_hosts.values())
        cap_host_kinds = []
        networking = "unknown"
        for cap in cap_hosts:
            cap_props = (cap.get("properties") if isinstance(cap, dict) else {}) or {}
            kind = cap_props.get("capabilityHostKind") or cap_props.get("kind") or (cap.get("kind") if isinstance(cap, dict) else None)
            if kind:
                cap_host_kinds.append(kind)
            if isinstance(cap, dict) and _capability_host_networking(cap) == "vnet-injected":
                networking = "vnet-injected"
        proj_id = proj.get("id")
        projects.append(
            {
                "id": proj_id,
                "name": proj.get("name"),
                "capabilityHosts": cap_host_kinds,
                "capabilityHostNetworking": networking,
            }
        )
        if proj_id:
            ctx.add_relationship(resource_id, proj_id, "FOUNDRY_HAS_PROJECT", "resource-id")

    fact = {"count": len(projects), "projects": projects}

    # Normalized, standard-independent aggregates for rule evaluation.
    kinds: set[str] = set()
    for proj in projects:
        kinds.update(proj.get("capabilityHosts") or [])
    net_states = [p.get("capabilityHostNetworking") for p in projects]
    if not projects or any(s == "unknown" for s in net_states):
        all_vnet_injected: Any = "unknown"
    else:
        all_vnet_injected = all(s == "vnet-injected" for s in net_states)
    fact["capabilityHostKinds"] = sorted(kinds)
    fact["allVnetInjected"] = all_vnet_injected

    status = EvidenceStatus.SUCCEEDED if isinstance(raw, dict) else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "projects", fact, raw, api_versions.COGNITIVE_SERVICES_PROJECTS, status)
    return ok()
