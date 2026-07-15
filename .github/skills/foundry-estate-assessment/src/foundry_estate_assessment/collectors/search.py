"""Azure AI Search collector: configuration and index footprint.

Never retrieves or persists admin/query keys or credentials embedded in data
source definitions.
"""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, _first_sku_name, ok


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(resource_id, api_versions.SEARCH)
    props = raw.get("properties") or {} if isinstance(raw, dict) else {}
    pe = props.get("privateEndpointConnections") or []
    footprint = props.get("assessmentFootprint") or {}

    fact = {
        "sku": _first_sku_name(raw.get("sku")) if isinstance(raw, dict) else None,
        "replicaCount": props.get("replicaCount"),
        "partitionCount": props.get("partitionCount"),
        "semanticSearch": props.get("semanticSearch"),
        "location": raw.get("location") if isinstance(raw, dict) else None,
        "publicNetworkAccess": props.get("publicNetworkAccess"),
        "privateEndpointCount": len(pe),
        "hasPrivateEndpoint": len(pe) > 0,
        "disableLocalAuth": props.get("disableLocalAuth"),
        "authOptions": props.get("authOptions"),
        "indexCount": footprint.get("indexCount"),
        "indexerCount": footprint.get("indexerCount"),
        "skillsetCount": footprint.get("skillsetCount"),
        "dataSourceCount": footprint.get("dataSourceCount"),
        "documentCount": footprint.get("documentCount"),
        "storageGB": footprint.get("storageGB"),
        "vectorIndexGB": footprint.get("vectorIndexGB"),
        "largestIndexGB": footprint.get("largestIndexGB"),
        "metricTimestamp": footprint.get("metricTimestamp"),
        "referencingResourceCount": len(ctx.db.relationships_to(ctx.snapshot_id, resource_id)),
    }
    if footprint.get("storageGB") is not None:
        ctx.add_metric(resource_id, "searchStorageGB", float(footprint["storageGB"]), "GB", footprint.get("metricTimestamp"))
    status = EvidenceStatus.SUCCEEDED if isinstance(raw, dict) and raw else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "search", fact, raw, api_versions.SEARCH, status)
    return ok()
