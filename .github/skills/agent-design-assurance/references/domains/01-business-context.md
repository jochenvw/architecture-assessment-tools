# Domain 01 — Business context and workload characteristics

Prefix `BC` · Establish what the application must achieve and the load it carries **before** judging any design choice.

## Method

1. Read README, docs, ADRs, issue/backlog exports and any briefing in the selected workload profile.
2. Treat briefing statements as claims to verify (`perspective: briefing`), never as evidence of implementation.
3. Record every quantity in `workload-characteristics.json` with an explicit `value_type`: `measured`, `configured_limit`, `business_target`, `estimate`, `briefing` or `unknown`.
4. Never derive a business target from code (a `max_tokens` setting is a configured limit, not a requirement).

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| BC-01 | Business purpose and intended outcomes | What business problem is solved; what outcome changes; who benefits. | README, product docs, briefing |
| BC-02 | Users and consuming applications | Human user roles, consuming systems, entry channels (UI, API, batch, Teams). | Docs, front-end routes, API specs |
| BC-03 | Functional requirements | Documented capabilities and their acceptance criteria; which are implemented vs planned. | Requirements docs, tests, backlog |
| BC-04 | Non-functional requirements | Documented latency, throughput, availability, accuracy, security, residency targets. | NFR docs, SLOs, IaC SKUs |
| BC-05 | Business criticality and consequence of error | Impact of incorrect, incomplete or late results; who relies on outputs downstream. | Docs, briefing, risk registers |
| BC-06 | Required accuracy and completeness | Stated precision/recall/coverage expectations; whether completeness is a hard requirement. | Acceptance criteria, eval thresholds |
| BC-07 | Latency and throughput requirements | Interactive vs batch expectations; per-item and end-to-end time budgets. | NFRs, timeouts, queue configs |
| BC-08 | Input characteristics | Document formats, sizes, page counts, volumes; facts or claims per document; corpus size. | Samples metadata (not content), ingestion configs |
| BC-09 | Concurrency and demand profile | Concurrent users/executions; peak vs average; reporting cycles; seasonality. | Telemetry aggregates, docs, scaling configs |
| BC-10 | Human oversight requirements | Mandated review, approval, sign-off and segregation of duties. | Process docs, UI flows, briefing |
| BC-11 | Business acceptance criteria | How the business decides the solution is fit for production. | UAT plans, eval gates, sign-off docs |
| BC-12 | Development maturity and production readiness | Current stage (PoC, pilot, production); environments live; users onboarded. | Deployment configs, release notes, CI/CD |
| BC-13 | Documented challenges and outstanding work | Known issues, TODO clusters, backlog themes, technical debt the team has named. | Issues, TODOs (counts + themes), docs |

## Capture rules

- Quantities: value, unit, period, environment, `value_type`, source.
- Input characteristics: describe formats and size bands; never copy document content.
- Maturity stage is descriptive (`PoC`, `pilot`, `production`), not a score.

## Signals → targeted questions

- Completeness is stated as mandatory but no measurement exists → ask how completeness is evidenced at acceptance.
- Peak periods are tied to reporting cycles → ask for the peak volume and the deadline that constrains it.
- Briefing claims a capability that has no implementation trace → ask where it lives (`unknown`, not `absent`).
