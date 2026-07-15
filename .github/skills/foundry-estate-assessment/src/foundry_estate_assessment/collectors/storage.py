"""Azure Storage collector: configuration and capacity footprint."""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, _first_sku_name, ok


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(resource_id, api_versions.STORAGE)
    props = raw.get("properties") or {} if isinstance(raw, dict) else {}
    pe = props.get("privateEndpointConnections") or []
    footprint = props.get("assessmentFootprint") or {}

    fact = {
        "kind": raw.get("kind") if isinstance(raw, dict) else None,
        "sku": _first_sku_name(raw.get("sku")) if isinstance(raw, dict) else None,
        "replication": (raw.get("sku") or {}).get("name") if isinstance(raw, dict) and isinstance(raw.get("sku"), dict) else None,
        "hierarchicalNamespaceEnabled": props.get("isHnsEnabled", False),
        "location": raw.get("location") if isinstance(raw, dict) else None,
        "publicNetworkAccess": props.get("publicNetworkAccess"),
        "networkAcls": props.get("networkAcls"),
        "allowSharedKeyAccess": props.get("allowSharedKeyAccess"),
        "privateEndpointCount": len(pe),
        "hasPrivateEndpoint": len(pe) > 0,
        "containerCount": footprint.get("containerCount"),
        "blobCount": footprint.get("blobCount"),
        "usedCapacityGB": footprint.get("usedCapacityGB"),
        "largestContainerGB": footprint.get("largestContainerGB"),
        "metricTimestamp": footprint.get("metricTimestamp"),
        "referencingResourceCount": len(ctx.db.relationships_to(ctx.snapshot_id, resource_id)),
    }
    if footprint.get("usedCapacityGB") is not None:
        ctx.add_metric(resource_id, "storageUsedGB", float(footprint["usedCapacityGB"]), "GB", footprint.get("metricTimestamp"))
    status = EvidenceStatus.SUCCEEDED if isinstance(raw, dict) and raw else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "storage", fact, raw, api_versions.STORAGE, status)
    return ok()
