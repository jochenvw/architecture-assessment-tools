"""APIM collector: AI Gateway configuration and backend authentication signals.

Never retrieves or exposes APIM subscription keys or secret named values. APIM
policies are sanitized before any raw evidence is written. Where backend
authentication cannot be proven from policy evidence, the collector returns
``unknown`` -- the mere presence of a managed identity is not treated as proof.
"""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, _first_sku_name, ok


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(resource_id, api_versions.APIM)
    props = raw.get("properties") or {} if isinstance(raw, dict) else {}
    identity = raw.get("identity") or {} if isinstance(raw, dict) else {}
    sku = raw.get("sku") if isinstance(raw, dict) else None
    sku_name = _first_sku_name(sku)
    footprint = props.get("assessmentFootprint") or {}

    # v2 tiers are the "Basic v2 / Standard v2 / Premium v2" generation.
    is_v2 = bool(sku_name) and sku_name.lower().endswith("v2")
    if not is_v2 and footprint.get("generation"):
        is_v2 = str(footprint.get("generation")).lower() == "v2"

    fact = {
        "sku": sku_name,
        "generation": "v2" if is_v2 else footprint.get("generation", "unknown"),
        "isV2": is_v2,
        "publicNetworkAccess": props.get("publicNetworkAccess"),
        "virtualNetworkType": props.get("virtualNetworkType"),
        "hasSystemAssignedIdentity": "systemassigned" in str(identity.get("type", "")).lower(),
        "identityType": identity.get("type"),
        # Backend-auth determination comes only from sanitized policy evidence.
        "apimToFoundryAuth": footprint.get("apimToFoundryAuth", "unknown"),
        "backendCentralFoundryIds": footprint.get("backendCentralFoundryIds", []),
        "teamScopedRoutes": footprint.get("teamScopedRoutes", "unknown"),
        "teamScopedProducts": footprint.get("teamScopedProducts", "unknown"),
        "teamScopedSubscriptions": footprint.get("teamScopedSubscriptions", "unknown"),
        "teamAuthMechanism": footprint.get("teamAuthMechanism", "unknown"),
        "apiCount": footprint.get("apiCount"),
        "productCount": footprint.get("productCount"),
        "backendCount": footprint.get("backendCount"),
    }
    for central_id in fact["backendCentralFoundryIds"]:
        ctx.add_relationship(resource_id, central_id, "APIM_TARGETS_CENTRAL_FOUNDRY", "apim-policy")
    # Team Foundries exposed through this gateway (proven from routing/policy evidence).
    for team_id in footprint.get("exposedFoundryIds", []) or []:
        ctx.add_relationship(team_id, resource_id, "FOUNDRY_EXPOSED_THROUGH_APIM", "apim-policy")

    status = EvidenceStatus.SUCCEEDED if isinstance(raw, dict) and raw else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "apim", fact, raw, api_versions.APIM, status)
    return ok()
