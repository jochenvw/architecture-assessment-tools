# Domain 12 — Lifecycle, traceability and operational ownership

Prefix `LT` · Everything that can change application behaviour must be versioned, governed and traceable to outputs.

## Method

1. List every behaviour-affecting artefact: code, agent definitions, models, prompts (including business-maintained prompts), dynamic configuration, tools, retrieval configuration, embeddings, index schemas, guardrails/policies, source documents.
2. For each, establish: where versioned, who approves change, how regressions are detected, how rollback works.
3. Provenance test: can a single generated output be linked to each artefact version **and** to the human review history?
4. Distinguish **operational observability** (traces, short retention) from **durable business auditability** (records kept for the business retention period).
5. Do not assume probabilistic outputs are exactly reproducible; ask whether historical reviews can be **reconstructed** (inputs, versions, evidence, decisions).

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| LT-01 | Application and agent definition versioning | Release versioning; agent definition versions; tagging. | CI/CD, agent registry |
| LT-02 | Model versioning, retirement and replacement | Pinned model versions; auto-upgrade settings; retirement monitoring; replacement process. | Deployments, docs |
| LT-03 | Prompt versioning and governance | Prompt storage, versioning, approval, diff/review, rollback; business-maintained prompts. | Prompt store schema, code |
| LT-04 | Dynamic configuration governance | Runtime-loaded config that alters behaviour; change control. | Code, stores |
| LT-05 | Tool and retrieval configuration versioning | Tool contract versions; retrieval parameters; index schema evolution; embedding upgrades. | Code, IaC |
| LT-06 | Guardrail and policy versioning | Versioning of content filters, policies and middleware rules. | IaC, config |
| LT-07 | Source document versioning | Whether the version of each source used is recorded. | Ingestion metadata |
| LT-08 | Release management and regression evaluation | Release process, regression evals per change type (code, prompt, model, index). | Pipelines, docs |
| LT-09 | Approval and rollback | Who approves which change; rollback per artefact type. | Docs, pipelines |
| LT-10 | Output provenance | Output linked to app/agent version, execution id, actual model, prompt versions, tool versions, retrieval config, source versions, evidence, guardrails, human review history. | Data model |
| LT-11 | Operational vs business auditability | Retention and immutability of audit records vs telemetry. | Data model, retention config |
| LT-12 | Historical review reconstruction | Ability to reconstruct a past review's inputs, versions, evidence and decisions. | Data model, docs |
| LT-13 | Operational and business ownership | Named owners for platform, application, prompts, models, data, support. | Docs, CODEOWNERS |
| LT-14 | Per-run lineage stamp | Whether every run records, together: code commit or release, prompt/instruction version, model and deployment, retrieval index version, and input content version (hash or version id — a filename is not a version). Note which elements are missing and where the stamp lives (trace attributes, run record). | Code, trace attributes, run data model |

## Signals → targeted questions

- Prompts loaded at runtime from a database → ask how versions, approvals and regression tests are managed, and whether a business edit can change mandatory behaviour.
- Output stores only the final text → ask how a disputed finding is traced to the evidence and model used.
- Model deployment set to auto-upgrade → ask how silent behaviour changes are detected.
- Inputs identified only by filename or path → ask how a re-uploaded document with the same name is distinguished from the original.
