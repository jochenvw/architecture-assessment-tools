"""Cosmos DB collector: configuration and non-double-counted footprint."""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, ok


def aggregate_regional_metric(samples: list[dict[str, Any]]) -> float:
    """Aggregate a metric that Azure reports per region without double-counting.

    Cosmos reports storage/document metrics per replicated region. The true
    account footprint is a single region's value, not their sum. We take the
    maximum observed per-region value (all replicas hold the same data).
    """
    values = [float(s.get("value", 0) or 0) for s in samples if s.get("value") is not None]
    return max(values) if values else 0.0


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(resource_id, api_versions.COSMOS_DB)
    props = raw.get("properties") or {} if isinstance(raw, dict) else {}
    pe = props.get("privateEndpointConnections") or []
    locations = props.get("locations") or props.get("readLocations") or []
    footprint = props.get("assessmentFootprint") or {}

    regional_samples = footprint.get("regionalDataGB") or []
    data_gb = aggregate_regional_metric(regional_samples) if regional_samples else footprint.get("dataGB")
    index_gb = footprint.get("indexGB")
    total_gb = None
    if data_gb is not None or index_gb is not None:
        total_gb = (data_gb or 0.0) + (index_gb or 0.0)

    api_type = raw.get("kind") if isinstance(raw, dict) else None
    capabilities = [c.get("name") for c in (props.get("capabilities") or [])]

    fact = {
        "apiType": api_type,
        "capabilities": capabilities,
        "regions": [loc.get("locationName") for loc in locations if isinstance(loc, dict)],
        "multiRegionWrite": props.get("enableMultipleWriteLocations"),
        "consistencyLevel": (props.get("consistencyPolicy") or {}).get("defaultConsistencyLevel"),
        "backupMode": (props.get("backupPolicy") or {}).get("type"),
        "publicNetworkAccess": props.get("publicNetworkAccess"),
        "privateEndpointCount": len(pe),
        "hasPrivateEndpoint": len(pe) > 0,
        "disableLocalAuth": props.get("disableLocalAuth"),
        "databaseCount": footprint.get("databaseCount"),
        "containerCount": footprint.get("containerCount"),
        "documentCount": footprint.get("documentCount"),
        "provisionedRU": footprint.get("provisionedRU"),
        "autoscaleMaxRU": footprint.get("autoscaleMaxRU"),
        "dataGB": data_gb,
        "indexGB": index_gb,
        "totalGB": total_gb,
        "largestContainerGB": footprint.get("largestContainerGB"),
        "metricTimestamp": footprint.get("metricTimestamp"),
        "referencingResourceCount": len(ctx.db.relationships_to(ctx.snapshot_id, resource_id)),
    }
    if data_gb is not None:
        ctx.add_metric(resource_id, "cosmosDataGB", float(data_gb), "GB", footprint.get("metricTimestamp"))
    status = EvidenceStatus.SUCCEEDED if isinstance(raw, dict) and raw else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "cosmos", fact, raw, api_versions.COSMOS_DB, status)
    return ok()
