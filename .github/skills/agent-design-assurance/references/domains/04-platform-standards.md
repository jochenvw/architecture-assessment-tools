# Domain 04 — Customer platform standards

Prefix `CS` (generic) + the platform profile's own prefix · Load the selected **platform profile** and assess the workload against it.

## Method

1. Resolve profiles with `ada.py profiles --profiles ...`. Platform criteria appear in `assessment.json` with `source_profile` set to the platform profile id.
2. Treat the profile's baseline as **the expected baseline to investigate**, not verified formal policy, unless the profile says `baseline_status: verified_policy`. Copy `expected_baseline.verified_policy` accordingly.
3. Trace identity and network flows **across component boundaries** (app → model, app → search, indexer → storage, agent → tools).
4. Distinguish **configured** isolation from **effective** connectivity, and **configured** managed identities from the authentication the code **actually** uses.
5. Record documented exceptions, waivers and unresolved policy requirements.

## Generic criteria (apply with any platform profile)

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| CS-01 | Platform standard identified | Which platform standard applies; its version and source; whether the team knows it. | Profile, docs, landing-zone references |
| CS-02 | Landing zone and subscription placement | Workload placement in a platform landing zone; shared vs dedicated resources. | IaC, Azure config |
| CS-03 | Network connectivity model conformance | BYO VNet, private endpoints, VNet integration/injection, inbound and outbound paths, private DNS, routing/firewall. | IaC, Azure config |
| CS-04 | Identity and keyless authentication conformance | Managed identity type (system vs user-assigned), keyless auth end to end, effective RBAC. | IaC, code, role assignments |
| CS-05 | Azure Policy compliance | Assigned policies, compliance state summary, exemptions. | `az policy state summarize`, docs |
| CS-06 | Diagnostics and telemetry conformance | Diagnostic settings, Log Analytics, Application Insights, agent-level distributed tracing. | IaC, Azure config |
| CS-07 | Infrastructure as Code and environment separation | All resources in IaC; separate subscriptions/resource groups per environment; promotion path. | IaC, CI/CD |
| CS-08 | Data residency | Regions of data stores, model deployments (global vs data-zone vs regional), telemetry. | IaC, deployments |
| CS-09 | Exceptions and waivers | Documented deviations, their owner and expiry; unresolved requirements. | Docs, policy exemptions |

## Platform profile criteria

Listed in the profile YAML (`criteria:`), each with an `expected_baseline` and `baseline_source`. Assess them with the same evidence and scoring model. Platform criteria often overlap `CS-*`, `WA-*` and `SG-*`; reference the related IDs instead of duplicating evidence.

## Pitfalls

- `publicNetworkAccess: Disabled` with no private endpoint means **unreachable**, not "secure" — check the actual path.
- A user-assigned identity in IaC is irrelevant if the code authenticates with a key from configuration.
- Policy compliance summary is point-in-time; record the timestamp and scope.
