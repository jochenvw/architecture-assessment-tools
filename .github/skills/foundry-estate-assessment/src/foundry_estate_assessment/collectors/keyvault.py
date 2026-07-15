"""Key Vault collector: configuration and object metadata counts only.

This collector never retrieves secret, key or certificate values. It records
``secretValuesRead = false`` and prefers counts / metadata. Object counts are
recorded only when supplied by non-secret metadata evidence; otherwise they are
left unknown.
"""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, _first_sku_name, ok


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(resource_id, api_versions.KEY_VAULT)
    props = raw.get("properties") or {} if isinstance(raw, dict) else {}
    pe = props.get("privateEndpointConnections") or []
    footprint = props.get("assessmentFootprint") or {}  # non-secret metadata counts

    referencing = ctx.db.relationships_to(ctx.snapshot_id, resource_id)
    fact = {
        "sku": _first_sku_name(props.get("sku")) or ((props.get("sku") or {}).get("name") if isinstance(props.get("sku"), dict) else None),
        "location": raw.get("location") if isinstance(raw, dict) else None,
        "tenantId": props.get("tenantId"),
        "authorizationModel": "rbac" if props.get("enableRbacAuthorization") else "access-policies",
        "enableRbacAuthorization": props.get("enableRbacAuthorization"),
        "publicNetworkAccess": props.get("publicNetworkAccess"),
        "networkAcls": props.get("networkAcls"),
        "privateEndpointCount": len(pe),
        "hasPrivateEndpoint": len(pe) > 0,
        "softDeleteEnabled": props.get("enableSoftDelete"),
        "purgeProtectionEnabled": props.get("enablePurgeProtection"),
        "secretCount": footprint.get("secretCount"),
        "keyCount": footprint.get("keyCount"),
        "certificateCount": footprint.get("certificateCount"),
        "expiredObjectCount": footprint.get("expiredObjectCount"),
        "referencingResourceCount": len(referencing),
        "secretValuesRead": False,
    }
    status = EvidenceStatus.SUCCEEDED if isinstance(raw, dict) and raw else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "keyvault", fact, raw, api_versions.KEY_VAULT, status)
    return ok()
