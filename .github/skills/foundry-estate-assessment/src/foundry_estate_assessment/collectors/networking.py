"""Networking collector: private endpoints, DNS and hub/spoke topology signals.

Where deep network graph evidence is not available (peering state, DNS zone
links) the collector records ``unknown`` rather than guessing, so downstream
rules resolve to ``UNKNOWN`` instead of a false ``FAIL``.
"""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, ok


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(resource_id, api_versions.COGNITIVE_SERVICES)
    props = raw.get("properties") or {} if isinstance(raw, dict) else {}
    pe_connections = props.get("privateEndpointConnections") or []
    approved = [
        pe
        for pe in pe_connections
        if str(((pe.get("properties") or {}).get("privateLinkServiceConnectionState") or {}).get("status", "")).lower()
        == "approved"
    ]
    net_injection = props.get("networkInjections") or props.get("customSubDomainName")

    fact = {
        "publicNetworkAccess": props.get("publicNetworkAccess"),
        "foundryPrivateEndpointPresent": len(approved) > 0,
        "privateEndpointCount": len(pe_connections),
        "approvedPrivateEndpointCount": len(approved),
        # Deeper topology facts require dedicated network queries / permissions.
        "hubSpokePeering": "unknown",
        "privateDnsAssociation": "unknown",
        "capabilityHostVnetInjection": "vnet-injected" if props.get("networkInjections") else "unknown",
    }
    status = EvidenceStatus.SUCCEEDED if isinstance(raw, dict) and raw else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "networking", fact, raw, api_versions.COGNITIVE_SERVICES, status)
    return ok()
