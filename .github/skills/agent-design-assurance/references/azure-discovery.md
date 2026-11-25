# Azure discovery

Read-only collection of **deployed** configuration and **aggregated telemetry**. It runs only after
the requester answers "yes" to the single opening question (may I use the Azure CLI?). That one
"yes" covers both. Without it, discovery is repository-only.

## 1. Find the targets (do not ask)

1. `az account show`, `az account list --query "[].{id:id,name:name}"`.
2. Repository hints: `.azure/<env>/.env` (`AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`,
   `AZURE_ENV_NAME`), IaC parameter files, pipeline variables.
3. `az group list --subscription <id> --query "[].{name:name,tags:tags}"`; match names, prefixes and
   `azd-env-name` tags from step 2.
4. Infer the environment from names and tags; use `unknown` when unclear.
5. Collect **every** matching resource group you can read, one `collect` run each.

Real subscription and resource-group names are only passed on the command line. The package
stores aliases (`AZ-SUB-n`, `AZ-RG-n`), and the names are also aliased wherever they appear in
prose.

## 2. Flags

| Flag | Default | Notes |
|---|---|---|
| `--subscription` | required | ID or name; passed per command, `az account set` is never run |
| `--resource-group` | required | One RG per run; repeat for more |
| `--environment` | `unknown` | `development`, `test`, `acceptance`, `production`, `shared` or `unknown` |
| `--authorised-by` | `requester` | Role that said "yes" |
| `--execute` | off | Without it, `collect` and `telemetry` are dry runs |
| `--skip-telemetry` | off | `collect` queries every Application Insights component it finds unless set |
| `--days` | 30 | Telemetry window |

The Azure CLI must already be installed and logged in. The skill never installs it, never logs
in, and never installs CLI extensions.

## 3. Commands

```text
ada.py azure plan       --out P                                # templates only, nothing runs
ada.py azure preflight  --out P --subscription S --resource-group RG
ada.py azure collect    --out P --subscription S --resource-group RG --environment test --execute
ada.py azure telemetry  --out P --subscription S --resource-group RG --app APPI --execute   # manual re-run for one component
```

`collect` gathers inventory, configuration, model deployments, diagnostics, RBAC, policy and search
schemas, then aggregated telemetry for each Application Insights component in the resource group.

Every collector and its command template is printed by `plan`, and every outcome is recorded in
`azure-configuration.json` → `attempts`.

| Collector | What | Not collected |
|---|---|---|
| inventory | Resource IDs, types, kinds, locations | Tags with values, app settings |
| configuration | Per-type projection: SKU, identity type, public network access, local auth, private endpoints, TLS | Keys, connection strings, secrets |
| model_deployments | Model, version, SKU and capacity per deployment | Prompts, completions |
| diagnostics | Diagnostic categories and destinations | Log content |
| rbac | Role names and principal types at RG scope | Principal names (aliased) |
| policy | Compliance summary | — |
| search_definitions | Index, indexer and skillset **shape** (field names, types, vector config) | Documents (never queried) |
| telemetry | KQL `summarize` aggregates: `requests` (daily volume, p95, failure rate), `dependencies_by_type`, `throttling`, `genai_usage` (tokens, if emitted), `exceptions_by_type` | Request content, prompts, responses, user IDs |

## 4. Safety model (`azure.guard`)

- **Allow-list of verbs:** `show`, `list`, `query`, `summarize`, `version`.
- **Deny-list of tokens:** anything secret-bearing or mutating, e.g. `keys`, `list-keys`, `secret`,
  `token`, `connection-string`, `appsettings`, `create`, `update`, `delete`, `set`, `assign`,
  `invoke`, `deploy`, `regenerate`, `login`, `export`, `run-command`, `ssh`.
- **Denied options:** `--show-secrets`, `--password`, `--account-key`, `--sas-token`,
  `--connection-string`, `--auth-mode`, `--include-secrets`.
- `az rest` is only allowed as `GET` to `*.search.windows.net/{indexes|indexers|skillsets}`.
- Output is cleaned with `sanitize.clean_value` and aliased **before** being written to the
  package. Real names exist only in `_work/alias-map.json`.

## 5. Failure handling

Every failure is recorded, never fatal to the discovery:

| Outcome | Meaning | Effect |
|---|---|---|
| `cli_missing` | `az` not on PATH | Repository-only; noted in `evidence_sources_unavailable` |
| `not_authenticated` | Not logged in | Same |
| `forbidden` | No Reader access | Attempt recorded; criteria stay `U` with attempts |
| `not_found` | Wrong RG or subscription | Same |
| `extension_missing` | CLI extension needed | Not installed; recorded |
| `timeout`, `error` | Other | Recorded |
| `blocked_by_guard` | Command failed the guard | Recorded; indicates a bug, report it |

## 6. Using the results

`collect` writes `azure-configuration.json` resources and `AZ-*` evidence items
(`perspective: deployed`), updates the manifest scope and modes, and adds the environment. Then:

1. Link `AZ-*` evidence to criteria in domains 03, 04, 10 and 11.
2. Add `azure_resource` entities and relationships to `architecture.json`.
3. Compare `deployed` with `declared` (IaC). Drift is `conflicting` evidence and a strong question.
4. Telemetry adds `runtime` evidence (`EV-TEL-*`) and `measured` workload characteristics
   (`WL-TEL-*`) to `workload-characteristics.json`.
