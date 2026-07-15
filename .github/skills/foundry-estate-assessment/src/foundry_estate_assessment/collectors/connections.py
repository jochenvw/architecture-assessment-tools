"""Connections collector: resolve project/account connections and register
peripheral data resources with proven relationships."""

from __future__ import annotations

from typing import Any, Optional

from .. import api_versions
from ..models import EvidenceStatus
from ..scheduler import TaskOutcome
from . import CollectorContext, ok, parse_resource_group, parse_subscription

# category (lower-cased) -> (relationship_type, peripheral classification, resource_type)
_CATEGORY_MAP = {
    "azurekeyvault": ("PROJECT_USES_KEYVAULT", "keyvault", "microsoft.keyvault/vaults"),
    "keyvault": ("PROJECT_USES_KEYVAULT", "keyvault", "microsoft.keyvault/vaults"),
    "cosmosdb": ("PROJECT_USES_COSMOS", "cosmos", "microsoft.documentdb/databaseaccounts"),
    "cosmosdbnosql": ("PROJECT_USES_COSMOS", "cosmos", "microsoft.documentdb/databaseaccounts"),
    "azurestorageaccount": ("PROJECT_USES_STORAGE", "storage", "microsoft.storage/storageaccounts"),
    "azureblob": ("PROJECT_USES_STORAGE", "storage", "microsoft.storage/storageaccounts"),
    "azurestorage": ("PROJECT_USES_STORAGE", "storage", "microsoft.storage/storageaccounts"),
    "cognitivesearch": ("PROJECT_USES_SEARCH", "search", "microsoft.search/searchservices"),
    "azureaisearch": ("PROJECT_USES_SEARCH", "search", "microsoft.search/searchservices"),
}


def _target_account_id(target: Optional[str]) -> Optional[str]:
    """Reduce a data-plane target (e.g. a KV secret URI) to its account ARM id."""
    if not target:
        return None
    if target.startswith("/subscriptions/"):
        # Trim to the account resource id (strip child paths for known types).
        return target
    return None


def _process_connections(ctx: CollectorContext, foundry_id: str, source_id: str, raw: Any) -> list[dict[str, Any]]:
    values = raw.get("value", []) if isinstance(raw, dict) else []
    connections = []
    for conn in values:
        props = conn.get("properties") or {}
        category = str(props.get("category", "")).lower()
        auth_type = props.get("authType")
        target = props.get("target") or props.get("resourceId") or (props.get("metadata") or {}).get("resourceId")
        account_id = _target_account_id(target if isinstance(target, str) else None)
        record = {
            "name": conn.get("name"),
            "category": props.get("category"),
            "authType": auth_type,
            "target": target,
            "targetResourceId": account_id,
        }
        connections.append(record)
        mapping = _CATEGORY_MAP.get(category)
        if mapping and account_id:
            rel_type, classification, res_type = mapping
            ctx.register_resource(
                {
                    "resource_id": account_id,
                    "subscription_id": parse_subscription(account_id),
                    "resource_group": parse_resource_group(account_id),
                    "name": account_id.rstrip("/").split("/")[-1],
                    "resource_type": res_type,
                    "kind": None,
                    "sku": None,
                    "location": None,
                    "tags": {},
                    "classification": classification,
                    "properties": {},
                }
            )
            ctx.add_relationship(source_id, account_id, rel_type, "connection")
    return connections


def collect(ctx: CollectorContext, resource_id: str) -> TaskOutcome:
    account_raw = ctx.client.rest_get(resource_id, api_versions.COGNITIVE_SERVICES, sub_path="/connections")
    connections = _process_connections(ctx, resource_id, resource_id, account_raw)

    # Project-scoped connections.
    projects_raw = ctx.client.rest_get(resource_id, api_versions.COGNITIVE_SERVICES_PROJECTS, sub_path="/projects")
    project_values = projects_raw.get("value", []) if isinstance(projects_raw, dict) else []
    for proj in project_values:
        proj_id = proj.get("id")
        if not proj_id:
            continue
        proj_conn_raw = ctx.client.rest_get(proj_id, api_versions.COGNITIVE_SERVICES_PROJECTS, sub_path="/connections")
        connections.extend(_process_connections(ctx, resource_id, proj_id, proj_conn_raw))

    fact = {"count": len(connections), "connections": connections}
    # Normalized: do all data-plane connections use Microsoft Entra ID auth?
    data_categories = {"azurekeyvault", "keyvault", "cosmosdb", "cosmosdbnosql",
                       "azurestorageaccount", "azureblob", "azurestorage",
                       "cognitivesearch", "azureaisearch"}
    entra_tokens = {"aad", "entra", "entraid", "managedidentity", "aadauth", "identity"}
    data_conns = [c for c in connections if str(c.get("category", "")).lower() in data_categories]
    if not data_conns:
        fact["dataConnectionAuthEntra"] = "unknown"
    elif any(c.get("authType") is None for c in data_conns):
        fact["dataConnectionAuthEntra"] = "unknown"
    else:
        fact["dataConnectionAuthEntra"] = all(
            str(c.get("authType", "")).lower().replace(" ", "") in entra_tokens for c in data_conns
        )
    status = EvidenceStatus.SUCCEEDED if isinstance(account_raw, dict) else EvidenceStatus.UNKNOWN
    ctx.store_fact(resource_id, "connections", fact, {"account": account_raw, "projects": projects_raw}, api_versions.COGNITIVE_SERVICES, status)
    return ok()
