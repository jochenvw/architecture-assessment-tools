"""Observability collector: diagnostic settings and telemetry destinations."""

from __future__ import annotations

from typing import Any

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, ok


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    raw = ctx.client.rest_get(
        resource_id,
        api_versions.INSIGHTS_DIAGNOSTICS,
        sub_path="/providers/Microsoft.Insights/diagnosticSettings",
    )
    values = raw.get("value", []) if isinstance(raw, dict) else []
    workspaces: list[str] = []
    app_insights: list[str] = []
    categories: set[str] = set()
    for setting in values:
        props = setting.get("properties") or {}
        if props.get("workspaceId"):
            workspaces.append(props["workspaceId"])
        # App Insights export presents as a storage/eventhub/workspace target;
        # a linked component id may appear in metrics/logs destinations.
        for log in props.get("logs") or []:
            if log.get("enabled") and log.get("category"):
                categories.add(log["category"])
            if log.get("enabled") and log.get("categoryGroup"):
                categories.add(log["categoryGroup"])

    for workspace_id in workspaces:
        ctx.add_relationship(resource_id, workspace_id, "RESOURCE_SENDS_TELEMETRY_TO_WORKSPACE", "diagnostic")

    fact = {
        "diagnosticSettingsCount": len(values),
        "diagnosticSettingsConfigured": len(values) > 0,
        "workspaces": sorted(set(workspaces)),
        "applicationInsights": sorted(set(app_insights)),
        "categories": sorted(categories),
    }
    status = EvidenceStatus.SUCCEEDED if isinstance(raw, dict) else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "observability", fact, raw, api_versions.INSIGHTS_DIAGNOSTICS, status)
    return ok()
