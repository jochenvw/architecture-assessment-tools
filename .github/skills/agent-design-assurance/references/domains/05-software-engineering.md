# Domain 05 — Software engineering and application architecture

Prefix `SE` · Reconstruct the application's structure from entry points inward. Semantic reading, not keyword counting.

## Method

1. Identify entry points (HTTP handlers, queue/blob triggers, CLI, schedulers, UI routes).
2. Map components and their responsibilities; note which logic is reusable and which is tightly coupled to one flow.
3. Record design rationale only where documented. Never invent rationale; mark `design_rationale.documented: false` when inferred.
4. TODO/FIXME clusters: report counts and themes, not verbatim comments.

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| SE-01 | Entry points and component boundaries | Entry points; components; responsibilities; dependency direction. | Source tree, routing, DI setup |
| SE-02 | Separation of concerns and modularity | Business logic vs agent logic vs infrastructure access; reusable modules vs coupled code. | Source code |
| SE-03 | Configuration management | Where config lives; per-environment config; secrets vs settings; validation at startup. | Config files, env definitions |
| SE-04 | Dependency management and version pinning | Lockfiles, pinned versions, update process (Dependabot/Renovate). | Manifests, lockfiles, CI |
| SE-05 | API and data contracts | Public API contracts (OpenAPI), internal structured contracts (Pydantic, JSON Schema), versioning. | Specs, models |
| SE-06 | State management | Where execution state lives (memory, Cosmos, blob, thread store); durability; isolation per user/run. | Code, IaC |
| SE-07 | Error handling | Exception strategy, user-facing errors, partial failure handling, error propagation from tools/models. | Code |
| SE-08 | Asynchronous execution and concurrency | Async patterns, background jobs, parallelism limits, cancellation. | Code |
| SE-09 | Automated testing | Unit, integration and end-to-end tests; what they cover; whether they run in CI. | Tests, CI |
| SE-10 | Security and dependency scanning | SAST, secret scanning, dependency/container scanning in CI. | CI config |
| SE-11 | CI/CD and deployment automation | Build, test, deploy pipelines; environments; approvals; rollback. | Pipelines |
| SE-12 | IaC coverage and environment-specific configuration | Share of resources in IaC; parameter files per environment; manual steps. | IaC, docs |
| SE-13 | Technical debt | Documented debt, TODO themes, known shortcuts and their risk. | Comments (themes), issues |
| SE-14 | Architecture decisions and rejected alternatives | ADRs or equivalent; alternatives considered. Populate `design-decisions.json`. | ADRs, docs |

## Signals → targeted questions

- Agent orchestration mixed into HTTP handlers → ask how the flow is tested independently of the API.
- No integration tests touching the model/search clients → ask how regressions in prompt or retrieval behaviour are detected.
- Config read ad hoc from environment variables across modules → ask how misconfiguration is detected before runtime.
