# Architecture extraction

`architecture.json` (graph) and `execution-flows.json` (ordered behaviour) let the reviewer draw
diagrams without the source. Capture only what evidence supports, and make unknowns explicit.

## 1. Entities

| Field | Rule |
|---|---|
| `id` | Stable: `ENT-<kind>-<n>`, e.g. `ENT-AGENT-1`. Reference Azure resources by alias. |
| `type` | `agent`, `workflow`, `model`, `model_deployment`, `tool`, `mcp_server`, `search_index`, `knowledge_base`, `data_store`, `source_system`, `identity`, `virtual_network`, `subnet`, `private_endpoint`, `gateway`, `human_approval_step`, `telemetry_destination`, `prompt_store`, `guardrail`, `azure_resource`, … |
| `name`, `purpose` | Sanitised, semantic |
| `environment`, `region` | Use `unknown` rather than guessing |
| `parent` | Containment (subnet → VNet, deployment → account, tool → agent) |
| `azure_alias`, `azure_type` | For deployed resources (`AZ-SEARCH-1`, `Microsoft.Search/searchServices`) |
| `properties` | Relevant technical properties (SKU, auth mode, public access) |
| `unknown_properties` | Properties you looked for but could not establish |
| `perspectives` | `{declared, implemented, deployed, runtime}`: presence per perspective (`present`, `absent`, `conflicting`, `unknown`, `not_applicable`) |
| `evidence_refs`, `confidence` | Required |

## 2. Relationships

| Field | Values |
|---|---|
| `source`, `target`, `direction` | Entity IDs; `source_to_target` or `bidirectional` |
| `purpose`, `protocol` | "retrieve candidate passages", `HTTPS/REST`, `AMQP`, `in-process` |
| `authentication` | `managed_identity_system`, `managed_identity_user`, `entra_user_delegated`, `on_behalf_of`, `api_key`, `connection_string`, `sas`, `service_principal_*`, `in_process`, `anonymous`, `unknown` |
| `identity` | Entity ID of the identity used |
| `network_path` | `private_endpoint`, `vnet_integration`, `service_endpoint`, `public_restricted`, `public_internet`, `in_process`, `unknown` |
| `data_exchanged`, `data_classification` | Schema or classification level only, never values |
| `mode` | `synchronous`, `asynchronous`, `batch`, `event_driven` or `unknown` |
| `perspectives`, `evidence_refs`, `confidence` | As for entities |

## 3. Execution flows

One flow per entry point (API route, queue trigger, schedule, UI action). Each step has an `order`,
a `kind` (`trigger`, `model_call`, `tool_call`, `retrieval`, `decision`, `branch`, `loop`,
`parallel`, `human_approval`, `validation`, `guardrail`, `persist`, `output`, `error_handler`,
`end`), and a `determinism` (`deterministic`, `model_driven`, `human`, `unknown`). It also has
`actor` and `target` (entity IDs), `condition`, `next`, `retry`, `loop_bound` and `on_failure`.
The flow-level `orchestration` is `deterministic`, `model_driven`, `hybrid` or `unknown`.

Record who decides the next step. That is the core of the agent-engineering review.

## 4. Nine diagram views

Each view is a filter over the same graph:

| # | View | Entity types | Relationship attributes |
|---|---|---|---|
| 1 | Physical Azure | `azure_resource`, network, `private_endpoint` | `network_path` |
| 2 | Logical application | `application`, `service`, `agent`, `tool`, `data_store` | `purpose`, `protocol` |
| 3 | Network | `virtual_network`, `subnet`, `private_endpoint`, `private_dns_zone`, `firewall`, `gateway` | `network_path` |
| 4 | Identity and authorisation | `identity`, `user_role` + targets | `authentication`, `identity` |
| 5 | Data flow and lifecycle | `source_system`, `data_store`, `search_index`, `knowledge_base` | `data_exchanged`, `data_classification`, `mode` |
| 6 | Agent execution | `agent`, `workflow`, `model_deployment`, `tool`, `mcp_server`, `human_approval_step`, `guardrail` | flows + steps |
| 7 | Deployment and environments | `environment`, `pipeline`, `ci_cd` | `environment`, perspectives |
| 8 | Observability | `telemetry_destination` + emitters | `purpose` |
| 9 | Lifecycle and dependencies | `prompt_store`, `model`, `pipeline`, `external_system` | `parent`, dependencies |

## 5. Rules

- Do not invent components or connections. If a call target is unresolved, create no edge. Record
  it in `unknown_properties` and add a question.
- Declared-only components (in docs or IaC but not found in code) have `implemented: unknown` or
  `absent` in `perspectives`.
- `check` fails on edges that reference missing entities and on steps that reference missing
  steps or entities.
