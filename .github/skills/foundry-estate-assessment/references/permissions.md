# Permissions

The scanner reads control-plane configuration and a small set of resource-level footprint metrics.
It never reads secret material and never writes to Azure.

## Minimum access

- **Reader** on every subscription (or resource group / resource) in the requested scope.
- Ability to run **Azure Resource Graph** queries (granted by Reader).
- `az login` completed for the identity running the scan (user, service principal, or managed
  identity via `az login --identity`).

Reader is sufficient for the vast majority of checks because the assessment is configuration-centric.

## What each area needs

| Area | Access | Notes |
| --- | --- | --- |
| Inventory (Resource Graph) | Reader | Enumerates accounts + APIM services across scope. |
| Foundry / project / deployment config | Reader | ARM `GET` on the account and child collections. |
| Connections | Reader | Reads connection **metadata** (category, auth type, target) — never keys. |
| Networking | Reader | Private endpoints, public network access, VNet injection. |
| Key Vault / Cosmos / Storage / Search | Reader | Control-plane properties + footprint counts/sizes. |
| APIM (gateway) | Reader | SKU/identity/network + sanitized policy signals. Never subscription keys. |
| Diagnostic settings | Reader | `Microsoft.Insights/diagnosticSettings`. |

## What it deliberately does NOT need

- **No data-plane secret access.** It never calls Key Vault `secret get`, never lists Storage keys,
  never retrieves Cosmos or Search admin keys, and never reads APIM subscription keys.
- **No write permissions** of any kind.
- **No Graph (Entra) directory permissions.** Identity is read from `az account show` only.

## Handling missing access

When the identity cannot read part of the scope:

- Unreadable **subscriptions** are reported as coverage gaps (not passes). `--all-accessible` scans
  only what the identity can read and the report says so explicitly.
- A permission failure on a specific resource marks the task `BLOCKED_PERMISSION`; affected rules
  resolve to `UNKNOWN`. Re-run with `--retry-blocked` after access is granted; `resume` will fill the
  gaps without repeating completed work.

## Scoping the run

Prefer the narrowest scope that answers the question:

```bash
--resource-id <foundry-arm-id>          # a single Foundry
--resource-group <rg-arm-id> [...]      # one or more resource groups
--subscription <sub-id> [...]           # specific subscriptions
--all-accessible                         # everything readable (NOT tenant-wide)
--management-group <mg-id>               # where the identity is permitted
```
