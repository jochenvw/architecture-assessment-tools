# Domain 11 — Observability, reliability, scalability and economics

Prefix `OS` · Separate **instrumentation configured** from **telemetry actually emitted and collected**.

## Method

1. From code: tracing setup, exporters, span names, GenAI semantic-convention attributes, sampling, content-recording flags.
2. From Azure (authorised): diagnostic settings, Application Insights configuration, Log Analytics retention.
3. From telemetry (included when the requester allows Azure CLI use): **aggregated** KQL templates only, run by `ada.py azure collect`. Never export raw logs, prompts or responses.
4. Every number is `measured` (with period and environment), `configured_limit`, or `estimate`. Hypothetical scale limits and cost estimates are never presented as measured.

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| OS-01 | Telemetry platform | Azure Monitor, Log Analytics, Application Insights, OpenTelemetry exporters; workspace-based. | IaC, telemetry setup |
| OS-02 | Agent-specific instrumentation | Spans for agent runs, model calls, tool calls, retrieval, guardrail decisions; GenAI attributes (model, tokens). | Code, trace samples (aggregate) |
| OS-03 | Distributed trace correlation | Correlation across front end, API, agent, tools and data services. | Code, telemetry |
| OS-04 | Sampling, retention and content recording | Sampling rate, retention days, prompt/response content capture. | Config, Azure config |
| OS-05 | Dashboards and alerts | Operational dashboards, alert rules, ownership of alerts. | IaC, Azure config |
| OS-06 | Emitted-telemetry verification | Whether telemetry is actually arriving (aggregated counts by type over a period). | Telemetry aggregates |
| OS-07 | Runtime measurements | Executions per period, success/failure, duration distribution, model calls and tokens per execution, retrieval latency, retries. | Telemetry aggregates |
| OS-08 | Throttling, quotas and rate limits | Model TPM/RPM quotas, 429 rates, search throttling, retry policy. | Deployments, telemetry |
| OS-09 | Scaling and concurrency mechanisms | Horizontal/vertical scaling, parallelism, queueing, backpressure, contention. | IaC, code |
| OS-10 | Resilience of long-running executions | Partial execution recovery, idempotency, checkpointing, resumability. | Code |
| OS-11 | Capacity planning and bottlenecks | Which dependency saturates first under higher load — only where evidence supports it. | Telemetry, configs |
| OS-12 | Cost per business task | Cost per completed review/task (measured or estimated, labelled); main cost drivers. | Telemetry, pricing tiers |
| OS-13 | Shift-left computation opportunities | Work done at execution time that could move to ingestion time (pre-extraction, pre-indexing). | Flows, code |

## Telemetry templates (aggregate only)

See `azure-discovery.md` → *Telemetry mode*. Templates return counts, rates and percentiles grouped by day, dependency type or model — never row-level data.

## Signals → targeted questions

- Application Insights configured but no GenAI spans found in code → ask how model and tool calls are observed in production.
- No token metrics → ask how cost per review is known.
- Long-running reviews without checkpointing → ask what happens when a run fails at 80 %.
