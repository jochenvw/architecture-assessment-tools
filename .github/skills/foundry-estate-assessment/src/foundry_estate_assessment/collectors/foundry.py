"""Foundry account collector: ARM metadata and account-level configuration."""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, _first_sku_name, ok, partial


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(resource_id, api_versions.COGNITIVE_SERVICES)
    if not isinstance(raw, dict) or not raw:
        ctx.store_fact(resource_id, "foundry", {}, raw, api_versions.COGNITIVE_SERVICES, EvidenceStatus.UNKNOWN)
        return partial("foundry ARM metadata unavailable")

    props: dict[str, Any] = raw.get("properties") or {}
    identity = raw.get("identity") or {}
    pe_connections = props.get("privateEndpointConnections") or []
    approved = [
        pe
        for pe in pe_connections
        if str(((pe.get("properties") or {}).get("privateLinkServiceConnectionState") or {}).get("status", "")).lower()
        == "approved"
    ]

    fact = {
        "kind": raw.get("kind"),
        "sku": _first_sku_name(raw.get("sku")),
        "location": raw.get("location"),
        "provisioningState": props.get("provisioningState"),
        "publicNetworkAccess": props.get("publicNetworkAccess"),
        "allowProjectManagement": props.get("allowProjectManagement"),
        "customSubDomainName": props.get("customSubDomainName"),
        "identityType": identity.get("type"),
        "hasSystemAssignedIdentity": "systemassigned" in str(identity.get("type", "")).lower(),
        "userAssignedIdentityCount": len(identity.get("userAssignedIdentities") or {}),
        "privateEndpointCount": len(pe_connections),
        "approvedPrivateEndpointCount": len(approved),
        "networkAcls": props.get("networkAcls"),
        "disableLocalAuth": props.get("disableLocalAuth"),
    }
    ctx.store_fact(resource_id, "foundry", fact, raw, api_versions.COGNITIVE_SERVICES)
    return ok()
