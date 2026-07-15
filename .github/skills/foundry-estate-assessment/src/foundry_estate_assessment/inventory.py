"""Inventory: stable Foundry-estate discovery and classification.

Phase 1 of the assessment. Uses Azure Resource Graph to find candidate
cognitive-services accounts across the selected scope, classifies each one, and
persists a stable snapshot that becomes the denominator for all progress
reporting. Detailed collection never begins until inventory completes.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from .azure_cli import AzureClient, AzureError
from .database import Database
from .evidence import utcnow
from .models import ResourceClassification, Scope

# Resource Graph query for candidate Foundry / cognitive accounts. Kept as a
# module constant so the fixture backend can match on a stable substring.
FOUNDRY_CANDIDATES_QUERY = (
    "Resources "
    "| where type =~ 'microsoft.cognitiveservices/accounts' "
    "| project id, name, type, kind, location, tags, sku, properties, "
    "subscriptionId, resourceGroup"
)

# APIM services are discovered so the AI Gateway can be profiled without
# hard-coding its resource ID. Discovered services are classified "apim" and
# are not counted as candidate Foundries.
APIM_QUERY = (
    "Resources "
    "| where type =~ 'microsoft.apimanagement/service' "
    "| project id, name, type, kind, location, tags, sku, properties, "
    "subscriptionId, resourceGroup"
)


def classify(kind: Optional[str], properties: dict[str, Any]) -> str:
    """Classify a cognitive-services account from its ARM shape.

    Classification never relies solely on names or tags. Unknown shapes are
    recorded as ``unknown-cognitive-account`` rather than discarded.
    """
    normalized_kind = (kind or "").strip().lower()
    properties = properties or {}

    # A current Foundry account exposes AI project / capability-host support.
    allow_projects = properties.get("allowProjectManagement")
    if normalized_kind == "aiservices" and allow_projects:
        return ResourceClassification.FOUNDRY_CURRENT.value
    if normalized_kind == "aiservices":
        # AIServices without project management is a plain AI Services account
        # unless a classic hub workspace is associated.
        if properties.get("associatedWorkspaces") or properties.get("isClassicHub"):
            return ResourceClassification.FOUNDRY_CLASSIC_HUB.value
        return ResourceClassification.AI_SERVICES_ACCOUNT.value
    if normalized_kind == "openai":
        return ResourceClassification.AZURE_OPENAI_ACCOUNT.value
    if normalized_kind in ("hub", "project") or properties.get("associatedWorkspaces"):
        return ResourceClassification.FOUNDRY_CLASSIC_HUB.value
    if normalized_kind == "cognitiveservices":
        return ResourceClassification.AI_SERVICES_ACCOUNT.value
    return ResourceClassification.UNKNOWN_COGNITIVE_ACCOUNT.value


def _sku_name(sku: Any) -> Optional[str]:
    if isinstance(sku, dict):
        return sku.get("name")
    if isinstance(sku, str):
        return sku
    return None


def resolve_subscription_scope(client: AzureClient, scope: Scope) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (accessible-in-scope, unavailable) subscription dicts."""
    all_subs = client.list_subscriptions()
    accessible: list[dict[str, Any]] = []
    unavailable: list[dict[str, Any]] = []
    for sub in all_subs:
        sub_id = sub.get("id") or sub.get("subscriptionId")
        state = sub.get("state", "")
        record = {
            "subscription_id": sub_id,
            "name": sub.get("name"),
            "state": state,
            "accessible": True,
        }
        if state and state.lower() not in ("enabled", "warned", "pastdue"):
            record["accessible"] = False
            record["reason"] = f"subscription state is {state}"
            unavailable.append(record)
            continue
        if scope.kind in ("subscription",) and sub_id not in scope.values:
            continue
        if scope.kind == "resource-group" or scope.kind == "resource":
            target_subs = {v.split("/")[2] for v in scope.values if "/subscriptions/" in v}
            if sub_id not in target_subs:
                continue
        accessible.append(record)
    return accessible, unavailable


def run_inventory(
    db: Database,
    client: AzureClient,
    assessment_id: str,
    scope: Scope,
) -> str:
    """Discover candidate Foundries and persist a new inventory snapshot.

    Returns the created ``snapshot_id``. Idempotent for a given resource set:
    re-running produces identical resource rows within a snapshot.
    """
    snapshot_id = str(uuid.uuid4())
    created_at = utcnow()

    accessible, unavailable = resolve_subscription_scope(client, scope)

    db.create_snapshot(
        {
            "snapshot_id": snapshot_id,
            "assessment_id": assessment_id,
            "created_at": created_at,
            "scope_kind": scope.kind,
            "scope_values": ",".join(scope.values),
            "subscriptions_accessible": len(accessible),
            "subscriptions_inventoried": 0,
            "candidate_foundries": 0,
        }
    )

    sub_ids = [s["subscription_id"] for s in accessible if s["subscription_id"]]
    for sub in accessible:
        db.upsert_subscription(snapshot_id, sub)
    for sub in unavailable:
        db.upsert_subscription(snapshot_id, sub)

    rows: list[dict[str, Any]] = []
    if sub_ids:
        try:
            rows = client.graph_query(FOUNDRY_CANDIDATES_QUERY, subscriptions=sub_ids)
        except AzureError:
            rows = []

    candidates = 0
    for row in _dedupe_by_id(rows):
        resource_id = row.get("id")
        if not resource_id:
            continue
        # Scope narrowing for resource / resource-group scopes.
        if scope.kind == "resource" and resource_id not in scope.values:
            continue
        if scope.kind == "resource-group":
            if not any(resource_id.lower().startswith(v.lower()) for v in scope.values):
                continue
        properties = row.get("properties") or {}
        classification = classify(row.get("kind"), properties)
        db.upsert_resource(
            snapshot_id,
            {
                "resource_id": resource_id,
                "subscription_id": row.get("subscriptionId"),
                "resource_group": row.get("resourceGroup"),
                "name": row.get("name"),
                "resource_type": row.get("type"),
                "kind": row.get("kind"),
                "sku": _sku_name(row.get("sku")),
                "location": row.get("location"),
                "tags": row.get("tags") or {},
                "classification": classification,
                "properties": properties,
                "source_query": "FOUNDRY_CANDIDATES_QUERY",
                "discovered_at": created_at,
            },
        )
        candidates += 1

    # Discover AI Gateways (APIM) so gateway posture can be assessed without a
    # hard-coded resource ID. These are registered but not counted as
    # candidate Foundries.
    apim_rows: list[dict[str, Any]] = []
    if sub_ids:
        try:
            apim_rows = client.graph_query(APIM_QUERY, subscriptions=sub_ids)
        except AzureError:
            apim_rows = []
    for row in _dedupe_by_id(apim_rows):
        resource_id = row.get("id")
        if not resource_id:
            continue
        if scope.kind == "resource-group":
            if not any(resource_id.lower().startswith(v.lower()) for v in scope.values):
                continue
        db.upsert_resource(
            snapshot_id,
            {
                "resource_id": resource_id,
                "subscription_id": row.get("subscriptionId"),
                "resource_group": row.get("resourceGroup"),
                "name": row.get("name"),
                "resource_type": row.get("type"),
                "kind": row.get("kind"),
                "sku": _sku_name(row.get("sku")),
                "location": row.get("location"),
                "tags": row.get("tags") or {},
                "classification": "apim",
                "properties": row.get("properties") or {},
                "source_query": "APIM_QUERY",
                "discovered_at": created_at,
            },
        )

    db.update_snapshot_counts(
        snapshot_id,
        subscriptions_inventoried=len(accessible),
        candidate_foundries=candidates,
    )
    return snapshot_id


def _dedupe_by_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: str(r.get("id", ""))):
        rid = row.get("id")
        if rid in seen:
            continue
        seen.add(rid)
        out.append(row)
    return out
