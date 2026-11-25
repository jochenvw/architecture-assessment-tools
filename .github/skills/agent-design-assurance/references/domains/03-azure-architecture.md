# Domain 03 — Azure infrastructure and Well-Architected principles

Prefix `WA` · Lightweight discovery aligned with the five Azure Well-Architected Framework (WAF) pillars. This is **not** a formal WAF review or certification.

## Method

1. Build topology from IaC (declared) → reconcile with `ada.py azure collect` output (deployed) where authorised.
2. Record resource type, region, SKU/tier, hosting model, dependencies and environment for every entity in `architecture.json`.
3. Keep declared vs deployed separate: a private endpoint in Bicep does not prove one exists in production, nor that traffic uses it.
4. Cost and performance statements must be labelled `measured`, `configured` or `estimate`.

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| WA-01 | Infrastructure topology | Resources, regions, tiers, hosting, dependencies, environment boundaries. | IaC, Azure config |
| WA-02 | Security — network isolation | Public network access, private endpoints, VNet integration, firewall/NSG dependencies. | IaC, Azure config |
| WA-03 | Security — authentication and authorisation | Entra ID vs keys; managed identities; local auth disabled; app-level authZ. | IaC, client code, Azure config |
| WA-04 | Security — data protection and trust boundaries | Encryption at rest/in transit, CMK where required, TLS minimums, trust boundaries crossed. | IaC, Azure config |
| WA-05 | Reliability — availability requirements and design | Target availability vs SKU SLAs, zone redundancy, replicas. | NFRs, IaC, Azure config |
| WA-06 | Reliability — dependency failure handling | Behaviour when model, search, storage or DB fails; retries with backoff; circuit breaking; timeouts. | Code, SDK retry config |
| WA-07 | Reliability — backup, restore and disaster recovery | Backup policies (Cosmos, storage), index rebuild ability, DR region, RTO/RPO. | IaC, Azure config, runbooks |
| WA-08 | Reliability — regional dependencies and single points of failure | Single-region model deployments, single replica search, shared quotas. | IaC, deployments |
| WA-09 | Cost — tiers and consumption model | Pricing tiers; provisioned (PTU) vs pay-as-you-go/global/data-zone deployments; idle capacity. | IaC, deployments |
| WA-10 | Cost — model inference and unit economics | Token usage per business task; cost per completed review/task; duplication. | Telemetry aggregates, logs, estimates |
| WA-11 | Operational excellence — automation and configuration | IaC coverage, deployment automation, configuration management, drift. | CI/CD, IaC |
| WA-12 | Operational excellence — monitoring, alerting and procedures | Alerts, dashboards, runbooks, on-call/support model. | IaC alert rules, docs |
| WA-13 | Performance — sizing, concurrency and throughput | Resource sizing, worker concurrency, model TPM/RPM quotas, search replicas/partitions. | IaC, deployments, code |
| WA-14 | Performance — throttling and scaling mechanisms | 429 handling, autoscale rules, queue-based load levelling, bottlenecks. | Code, IaC, telemetry |

## Pillar mapping

Security WA-02..04 · Reliability WA-05..08 · Cost WA-09..10 · Operational excellence WA-11..12 · Performance WA-13..14. WA-01 underpins all.

## Signals → targeted questions

- Single model deployment in one region with no fallback → ask the impact of regional unavailability or quota exhaustion.
- Search with one replica in production → ask the availability target for retrieval.
- No backup policy on the store holding prompts or findings → ask how prompt/finding history is recovered.
- PTU and pay-as-you-go side by side → ask how traffic is routed and how spillover is handled.
