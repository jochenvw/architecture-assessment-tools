"""Model deployment collector: build the model footprint for a Foundry."""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, _first_sku_name, ok


def _deployment_record(foundry_id: str, dep: dict[str, Any], project_id: str | None = None) -> dict[str, Any]:
    props = dep.get("properties") or {}
    model = props.get("model") or {}
    return {
        "foundryResourceId": foundry_id,
        "projectResourceId": project_id,
        "deploymentName": dep.get("name"),
        "modelName": model.get("name"),
        "modelVersion": model.get("version"),
        "publisher": model.get("format") or model.get("publisher"),
        "skuName": _first_sku_name(dep.get("sku")),
        "capacity": (dep.get("sku") or {}).get("capacity") if isinstance(dep.get("sku"), dict) else None,
        "provisioningState": props.get("provisioningState"),
        "raiPolicy": props.get("raiPolicyName"),
        "collectionStatus": "SUCCEEDED",
    }


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(resource_id, api_versions.COGNITIVE_SERVICES, sub_path="/deployments")
    values = raw.get("value", []) if isinstance(raw, dict) else []
    deployments = [_deployment_record(resource_id, dep) for dep in values]
    fact = {"count": len(deployments), "deployments": deployments}
    status = EvidenceStatus.SUCCEEDED if isinstance(raw, dict) else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "model_deployments", fact, raw, api_versions.COGNITIVE_SERVICES, status)
    ctx.add_metric(resource_id, "modelDeploymentCount", float(len(deployments)))
    return ok()
