# Telemetry Maturity Path

How a customer moves from Foundry / Azure OpenAI **deployment-level** usage toward workload-level
**OpenTelemetry-based** quota planning. Use this when only Foundry usage is available so the estimate
is still produced *now*, but the customer also gets a concrete path to better evidence.

---

## Why this matters

Foundry deployment metrics answer: *"What did the model deployment consume?"*

OpenTelemetry / application telemetry answers: *"What did this agent, user journey, business
transaction, tool chain, or workflow consume?"*

Quota requests are more defensible when based on workload-level telemetry, because it captures:

- P95 input/output tokens per business transaction;
- fanout across RAG / tools / agents / guardrails;
- retries and throttles;
- P95 latency;
- concurrency;
- cache behavior;
- model / deployment / region dimensions.

> 💡 Scope this guidance to **Microsoft Agent Framework** agents. The key idea: **runtime ownership**
> (who runs the agent) and **observability destination** (where telemetry lands) are independent
> choices.

## Options

| Option | Runtime | Telemetry destination | Foundry visibility | Use when | Trade-off |
| --- | --- | --- | --- | --- | --- |
| 1. Foundry-hosted Agent Framework agent | Foundry Agent Service | App Insights connected to Foundry | Native | You want Foundry to own hosting, endpoint, lifecycle, and observability | Less control over runtime/platform |
| 2. Self-hosted Agent Framework + App Insights only | Container Apps, AKS, App Service, VM | Application Insights / Azure Monitor | Not necessarily Foundry | You own runtime and only need operational telemetry, KQL, dashboards, alerts | Does not automatically create Foundry agent trace/eval UX |
| 3. Self-hosted Agent Framework + external agent registration | Container Apps, AKS, App Service, VM | App Insights connected to Foundry project | Yes | You own runtime but want traces/evals to surface in Foundry | Requires external-agent registration and correct GenAI attributes |
| 4. Self-hosted Agent Framework calling Foundry APIs | Your runtime | Your choice: App Insights, other OTel backend, logs | No, unless instrumented/registered | You want Foundry models/tools but keep runtime and observability separate | Foundry API use alone does not equal Foundry observability |

## Decision tree

```text
Do you want Foundry to run the Agent Framework agent?
  Yes
    → Use Foundry-hosted agent.
    → Connect Foundry project to Application Insights.
    → Use Foundry-native tracing as the first telemetry source.

  No
    → Are App Insights / Azure Monitor dashboards enough?
        Yes
          → Self-host Agent Framework.
          → Instrument with OpenTelemetry / Azure Monitor OpenTelemetry.
          → Emit GenAI spans, metrics, logs to Application Insights.

        No
          → Do you want traces and evaluations to surface in Foundry?
              Yes
                → Self-host Agent Framework.
                → Export OpenTelemetry GenAI telemetry to the App Insights resource connected to the Foundry project.
                → Register the agent as an external agent in Foundry.
                → Ensure spans include the stable agent identity needed for Foundry trace association.

              No
                → Self-host Agent Framework and keep observability outside Foundry.
                → Use Foundry models/APIs if desired, but treat observability as application-owned.
```

## Required telemetry for quota planning

For OTel-based quota planning, capture at minimum:

| Signal | Why it matters |
|---|---|
| agent name / agent id | Attribute usage to the correct agent |
| workflow / operation name | Attribute usage to business transaction |
| model / deployment / region | Quota is model and region scoped |
| input tokens | TPM driver |
| output tokens | TPM driver and latency driver |
| total tokens | Sanity check |
| cached tokens, if available | Cache materially changes demand |
| retry count | Retries consume capacity |
| throttling / errors | Shows current quota pressure |
| latency P50/P95/P99 | Required for concurrency sizing |
| trace / request correlation id | Reconstruct full chain and fanout |
| tool / retrieval / model-call spans | Avoid missing agent/RAG fanout |

## Minimal instrumentation target

The minimum viable target is **not** "perfect observability." The minimum viable target for quota
planning is:

- per business transaction token totals;
- P95 input/output tokens;
- model/deployment dimension;
- retry/throttle count;
- P95 latency;
- fanout count;
- enough correlation to distinguish agents/workflows.

## Migration recommendation

If the customer only has Foundry usage today:

```text
Step 1 — Use Foundry deployment metrics for a coarse quota request.
Step 2 — Isolate deployments per workload or add gateway/application attribution where possible.
Step 3 — Add Agent Framework OpenTelemetry instrumentation into the self-hosted app,
         or rely on Foundry-native tracing for hosted agents.
Step 4 — Export to Application Insights.
Step 5 — If Foundry trace/eval UX is required for a self-hosted agent, register it as an external agent.
Step 6 — Re-run quota planning using P95 workload-level telemetry.
```

## Output snippet

Reusable report section to paste into a Foundry-only estimate (see also `report-template.md`):

```markdown
## Path to OTel-based quota planning

Today's estimate is based on Foundry deployment-level usage. That is sufficient for a coarse quota
request, but it does not attribute usage to individual agents, workflows, user journeys, retries,
tools, or prompt variants.

To tighten the estimate, move to workload-level telemetry:

1. If the agent can run inside Foundry, use a Foundry-hosted Agent Framework agent and connect the
   Foundry project to Application Insights.
2. If the agent stays self-hosted and App Insights is enough, instrument the Agent Framework service
   with OpenTelemetry and export GenAI traces/metrics/logs to Application Insights.
3. If the agent stays self-hosted but should also appear in Foundry traces/evaluations, export
   OpenTelemetry GenAI telemetry to the App Insights resource connected to Foundry and register the
   agent as an external agent.
4. If the app only calls Foundry APIs, treat Foundry as the model/tool provider; observability still
   needs application-level instrumentation unless the agent is hosted or registered.

The target telemetry for the next estimate should include P95 input/output tokens per business
transaction, full model-call fanout, retries, throttles, cache behavior, and P95 latency under
realistic concurrency.
```
