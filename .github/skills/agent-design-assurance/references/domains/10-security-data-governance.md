# Domain 10 — Security, identity and data governance

Prefix `SG` · Reconstruct trust boundaries, identity flows and the data lifecycle.

## Method

1. Draw (in `architecture.json`) every identity principal and every authenticated relationship: who calls what, as whom, over which network path.
2. Effective permissions come from role assignments in Azure (if authorised) — IaC role assignments are `declared` only.
3. Trace data from source → ingestion → storage → index → model context → agent state → telemetry → output. Include **derived data** (chunks, embeddings, summaries, findings).
4. Never retrieve secret values. Record **that** a secret is used and **where it is stored**, not the value.
5. No regulatory or certification claims. Describe controls; do not declare compliance.

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| SG-01 | User authentication and authorisation | Entra ID sign-in, app roles, per-feature authorisation. | Front-end/API auth code, app registrations (declared) |
| SG-02 | Workload and agent identities | App identities, agent identities, managed identities (system vs user-assigned) and their use. | IaC, code |
| SG-03 | Identity propagation and on-behalf-of | Whether user identity flows to downstream calls; OBO; data access as user vs as app. | Code |
| SG-04 | Service-to-service authorisation and RBAC | Role assignments, scopes, least privilege, data-plane vs control-plane roles. | Role assignments, IaC |
| SG-05 | Secrets and keyless authentication | Key Vault use, key-based auth remaining, local auth disabled, secret rotation. | IaC, code, Azure config |
| SG-06 | Network security | Private endpoints, public exposure, outbound restrictions, WAF/front door. | IaC, Azure config |
| SG-07 | Encryption | At rest (platform vs customer-managed keys), in transit, TLS version. | IaC, Azure config |
| SG-08 | Data classification and residency | Classification of processed data; regions of storage, processing and telemetry. | Docs, IaC |
| SG-09 | Source permission preservation | Whether users can only retrieve what they are entitled to see at source. | Index fields, filters |
| SG-10 | Retention and deletion | Retention for documents, derived data, findings, threads, telemetry; deletion propagation to derived data. | Config, lifecycle policies |
| SG-11 | Data lineage across the lifecycle | Ability to trace outputs and derived artefacts to sources and versions. | Data model |
| SG-12 | Sensitive information in logs and telemetry | Prompt/response logging, PII in traces, content recording settings. | Telemetry config |
| SG-13 | Isolation | Cross-environment, cross-user and cross-tenant isolation of data, state and indexes. | Code, IaC |
| SG-14 | External endpoints and trust relationships | Third-party APIs, outbound calls, trust of external content. | Code, config |
| SG-15 | Audit requirements and audit trail | Who did what, when; immutability; retention of audit data. | Data model, logs |
| SG-16 | Identity permission breadth (blast radius) | Per workload/agent identity: the broadest data it can reach versus what the use case needs — e.g. a whole search service versus one index, tenant-wide Graph scopes (`Sites.Read.All`) versus `Sites.Selected`, resource-group or subscription scope. Record what a compromised or prompt-injected identity could read or change. | Role assignments, app permissions (declared), IaC, code |
| SG-17 | Sensitivity label propagation | Whether source sensitivity labels or classifications (Microsoft Purview / Information Protection) are captured at ingestion, kept on chunks and index entries, used in retrieval, and applied to generated outputs (for example the highest source label). | Ingestion code, index schema, output model |

## Signals → targeted questions

- Telemetry content recording enabled → ask which data classes reach Application Insights and who can read them.
- Embeddings stored without deletion propagation → ask how deleted source documents are purged from derived stores.
- Contributor role at resource-group scope for the app identity → ask why data-plane roles were not sufficient.
- One identity with read access to every index or a tenant-wide Graph scope → ask which data the use case actually needs and whether sensitive sources are separated.
- Labelled source documents but no label field in the index or output → ask how output classification is determined.
