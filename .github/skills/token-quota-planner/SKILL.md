---
name: token-quota-planner
description: >-
  Use this skill when estimating model token quota or capacity from measured Foundry usage, Azure
  OpenAI usage, OpenTelemetry GenAI traces, application telemetry, gateway logs, load tests, smoke
  tests, manual PoC token samples, or benchmark runs. Use when the user wants to request or justify
  TPM, RPM, concurrency, deployment, regional, or model quota for production load. Do not use for
  pure cost estimation, historical billing analysis, vendor quotes, SLA guarantees, or generic
  observability setup.
---

# Token Quota Planner

Estimate the **peak model capacity** (TPM / RPM / concurrency) a workload needs in production from
measured token evidence, and produce a **defensible, executive-ready quota request pack**.

This is a **peak-capacity planning** skill, not a cost, billing, or accounting skill. The central
question is:

```text
How much peak model capacity do we need to avoid throttling under realistic production load?
```

The failure mode it exists to prevent:

```text
monthly tokens ÷ minutes/month = required TPM     ← wrong: quota is consumed at peaks, not averages
```

## Deployment evidence vs workload evidence

```text
Foundry usage is deployment evidence  → "this deployment consumed X tokens, peaked at Y."
Telemetry is workload evidence        → "this transaction uses P95 X in / Y out tokens, Z calls."
Quota requests need both if possible.
```

Telemetry is generally stronger for quota planning; Foundry usage is often easier to obtain. One
skill, multiple **evidence adapters**, one shared engine (representativeness gate → peak-demand model
→ quota math → McKinsey-style report).

> 🔑 **Foundry usage is deployment evidence. OpenTelemetry is workload evidence.** If only Foundry
> usage exists, still produce a coarse quota estimate **and** recommend a telemetry maturity path
> (`telemetry-maturity-path.md`) — never block the estimate.

## WHEN TO USE

- Token quota / TPM / RPM / concurrency / model capacity planning.
- Quota-increase justification or Foundry / Azure OpenAI quota request preparation.
- Scaling from PoC, load-test, telemetry, or gateway token measurements to production peak demand.
- Throttling-risk and concurrency sizing for model deployments.

## DO NOT USE FOR

- Pure cloud **cost** estimation or unit economics (use a cost-extrapolation skill instead).
- Historical spend trends, invoice analysis, or monthly token accounting.
- Vendor price quotes, SLA / capacity guarantees, or exact regional capacity promises.
- Model benchmarking or generic OpenTelemetry setup unless quota sizing is the goal.

## Intent routing

| User intent | Route |
| --- | --- |
| "Which evidence do I have / which path applies?" | `evidence-routing.md` |
| "I have Foundry / Azure OpenAI deployment usage" | `evidence-foundry-usage.md` |
| "I have OpenTelemetry / app / gateway traces" | `evidence-otel-telemetry.md` |
| "I only have manual PoC numbers" | `evidence-manual-poc.md` |
| "We only have Foundry token usage, no app telemetry. What now?" | `evidence-foundry-usage.md` + `telemetry-maturity-path.md` |
| "How do we move from Foundry usage to OTel-based quota planning?" | `telemetry-maturity-path.md` + `azure-foundry-notes.md` |
| "Our Agent Framework agent runs in Container Apps but should show in Foundry." | `telemetry-maturity-path.md` |
| "We run Agent Framework outside Foundry and only need App Insights logs." | `telemetry-maturity-path.md` |
| "How representative is my sample?" | `representativeness.md` |
| "Do the TPM/RPM/concurrency math" | `demand-model.md` |
| "Will production exceed my current quota / TPM limits?" | `demand-model.md` + `azure-foundry-notes.md` |
| "Normalize quota terms (current vs assigned vs available)" | `quota-normalization.md` |
| "Azure / Foundry specifics for the request pack" | `azure-foundry-notes.md` |
| "Produce the final report" | `report-template.md` |
| "Rules the estimate must obey" | `guardrails.md` |
| "Edge cases / missing data" | `error-handling.md` |
| "Show me worked examples" | `examples.md` |

## How to run this skill

1. **Route the evidence** (`evidence-routing.md`) — Foundry usage, OTel telemetry, manual PoC, or a
   combination. Reconcile, never blindly average, when more than one exists.
2. **Gather evidence** via the matching adapter and normalize it (`quota-normalization.md`).
3. **Score representativeness** (`representativeness.md`) — sets the safety multiplier, not the base
   demand.
4. **Build the peak-demand model** (`demand-model.md`) — peak RPM, P95 tokens, fanout, retries,
   required TPM/RPM/concurrency, then apply the safety multiplier. **When current quota is available,
   compare the recommended TPM against the current limit and free headroom** (on Azure: `az
   cognitiveservices usage list` + `account deployment list`) and state the verdict.
5. **Emit the report** (`report-template.md`) — executive answer first, with the mandatory
   coarse-estimate disclaimer — and **save it as a Markdown document** per the Output Contract below.
6. Obey every rule in `guardrails.md`.

## Output Contract (Required)

The deliverable is a **saved, properly formatted Markdown document**, not just an inline reply.
Before finishing, all of the following must be true:

1. The full report is written to a Markdown file named
   `token-quota-estimate-<workload-slug>-<YYYY-MM-DD>.md` in the current working directory (or a path
   the user specifies). State the saved file path in the final reply.
2. The document follows the exact structure in `report-template.md`: **Executive answer** first, then
   **Basis of estimate**, **Demand model**, **Quota request pack**, **Quota headroom check**,
   **Confidence and representativeness**, **Assumptions**, **Sensitivity**, **Missing or weak
   evidence**, **Recommended next measurements**, and the disclaimer last.
3. Markdown renders cleanly: a single H1 title, `##` section headings, GitHub-aligned tables, fenced
   code blocks where used, and no stray HTML or broken table rows.
4. TPM, RPM, and concurrency are reported **separately**; any figure resting on missing latency or
   request-count data is explicitly flagged **weak**; the representativeness score and safety
   multiplier are shown.
5. The mandatory **coarse-estimate disclaimer** is the final block of the document.
6. The inline chat reply contains the executive answer plus the saved file path; the file holds the
   full report.

## Sub-files

- `workflow.md` — the end-to-end procedure tying the adapters and engine together.
- `evidence-routing.md` — choose and reconcile evidence paths.
- `evidence-foundry-usage.md` — Foundry / Azure OpenAI deployment-usage adapter.
- `evidence-otel-telemetry.md` — OpenTelemetry / application-telemetry adapter.
- `evidence-manual-poc.md` — manual PoC adapter.
- `representativeness.md` — 0–12 gate, rating → safety multiplier, hard caps.
- `demand-model.md` — all peak-demand and quota formulas.
- `quota-normalization.md` — the quota evidence contract and quota-term taxonomy.
- `azure-foundry-notes.md` — platform-specific Azure/Foundry guidance and request-pack fields.
- `telemetry-maturity-path.md` — Foundry-only → OTel maturity options, decision tree, and Agent
  Framework observability patterns.
- `report-template.md` — the McKinsey-style, top-down report structure.
- `guardrails.md` — the hard rules the estimate must always obey.
- `examples.md` — four worked examples across the evidence paths.
- `error-handling.md` — what to do when evidence is missing, shared, sampled, or incomplete.
