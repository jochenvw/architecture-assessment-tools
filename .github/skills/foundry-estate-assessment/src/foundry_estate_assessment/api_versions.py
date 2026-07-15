"""Centralized Azure REST API versions.

All Azure REST API versions used by the collectors live here so that an API
version change never requires editing collector logic. Each collector imports
the version it needs from this module.
"""

from __future__ import annotations

# Control-plane / ARM providers.
COGNITIVE_SERVICES = "2025-06-01"  # Microsoft.CognitiveServices (Foundry / AI Services)
COGNITIVE_SERVICES_PROJECTS = "2025-06-01"
KEY_VAULT = "2023-07-01"  # Microsoft.KeyVault vaults
COSMOS_DB = "2024-11-15"  # Microsoft.DocumentDB databaseAccounts
STORAGE = "2023-05-01"  # Microsoft.Storage storageAccounts
SEARCH = "2024-06-01-preview"  # Microsoft.Search searchServices
APIM = "2024-05-01"  # Microsoft.ApiManagement service
NETWORK = "2024-05-01"  # Microsoft.Network (vnets, private endpoints, dns)
INSIGHTS_DIAGNOSTICS = "2021-05-01-preview"  # Microsoft.Insights/diagnosticSettings
APPLICATION_INSIGHTS = "2020-02-02"  # Microsoft.Insights/components
LOG_ANALYTICS = "2023-09-01"  # Microsoft.OperationalInsights/workspaces
MONITOR_METRICS = "2024-02-01"  # Microsoft.Insights metrics
RESOURCE_GRAPH = "2022-10-01"  # Microsoft.ResourceGraph

# Data-plane API versions (used only for metadata / counts, never for secrets).
SEARCH_DATA_PLANE = "2024-07-01"
KEY_VAULT_DATA_PLANE = "7.4"


def all_versions() -> dict[str, str]:
    """Return a mapping of API-version constant names to their values."""
    return {
        name: value
        for name, value in globals().items()
        if name.isupper() and isinstance(value, str)
    }
