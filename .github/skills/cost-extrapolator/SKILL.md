---
name: cost-extrapolator
description: >-
  Use this skill when estimating production workload cost from a small measured PoC, benchmark,
  smoke test, billing sample, token sample, batch run, document-processing sample, API load test,
  or other measured unit-cost evidence. Use when the user wants to scale from measured sample volume
  to target production volume and needs assumptions, representativeness, confidence bands, one-time
  versus recurring cost, fixed versus variable cost, or unit-economics decomposition. Do not use for
  pure historical billing analysis, vendor quote generation, or time-series spend forecasting.
---

# Cost Extrapolator

Project the production cost of a workload from a small measured proof-of-concept (PoC) run.

This skill behaves like a sober cost engineer, not a spreadsheet optimist. It refuses to
extrapolate blindly: before producing numbers it runs a small representativeness gate, and the
representativeness score controls the **width of the confidence band**, not the point estimate.

The core failure mode this skill exists to prevent:

```text
measured cost × naive scale factor
```

Never do that unless the assumptions and confidence band make the risk explicit.

## Mental model

This is **not** a historical billing forecast ("extend past spend over time"). It is a
**bottom-up unit-economics scaling problem**:

```text
production cost = fixed baseline + variable unit cost × target volume
```

...but only after decomposing the measured cost and checking whether the measured sample was
representative. Always report a band, never a bare point estimate, and lead with the answer
(top-down, Pyramid Principle):

```text
Assuming the measured period (1–7 Jun) and the cost over the workload scope are representative of
steady-state serving load, extrapolating to 500K queries/day leads to ~€4,800/month — range
€2,900–€8,600 (±40%, Medium confidence) — assuming model output tokens and concurrency hold.
Dominant drivers: model output tokens, query count, always-on infrastructure.
```

## WHEN TO USE

- Scaling a measured PoC / smoke test / benchmark to a target production volume.
- Estimating cost for "we processed N documents for €X, what about M/week?".
- Extrapolating from a billing sample, token sample, batch run, or API load test.
- Decomposing measured cost into fixed vs variable and one-time vs recurring.
- Judging how representative a PoC is before trusting any extrapolation.

## DO NOT USE FOR

- Pure historical billing analysis or month-over-month spend trends.
- Time-series spend forecasting (use a billing/forecasting workflow instead).
- Generating a precise vendor quote or contract price.
- Anything requiring a single exact number with no uncertainty.

## Intent routing

| User intent | Route |
| --- | --- |
| "We processed 2 docs; what about 100/week?" | `workflow.md` + `representativeness.md` |
| "Here is yesterday's cost from cloud billing; extrapolate production" | `cost-normalization.md` + `workflow.md` |
| "How representative is this PoC?" | `representativeness.md` |
| "Break down fixed vs variable cost" | `workflow.md` |
| "Give a precise vendor quote" | Do not use; explain limitation (`error-handling.md`) |
| "Analyze historical monthly cloud spend trend" | Do not use; use billing/forecasting workflow instead |
| Edge cases, missing data, contradictions | `error-handling.md` |
| Rules the estimate must always obey | `guardrails.md` |
| Worked end-to-end examples | `examples.md` |

## Required inputs (quick reference)

| Input | Required? | Example |
| --- | ---: | --- |
| Measured unit count | Yes | 2 documents, 100 requests, 1 batch run |
| Measured cost | Yes | €0.42 |
| Cost scope | Yes | workload only, resource group, tagged resources |
| Cost time window | Yes if billing-derived | yesterday UTC, 1-hour test |
| Target production volume | Yes | 100 docs/week, 1M req/day |
| Unit type | Yes | document, request, batch run, user |
| One-time vs recurring paths | Yes | indexing and serving both included? |
| Infrastructure realism | Yes | dev tier vs production-like |
| Unit mix realism | Yes | simple docs vs realistic distribution |
| Token/usage metrics | If LLM workload | input/output tokens, cache, retries |

## How to run this skill

1. Gather the required inputs above. If the user gave enough unprompted, do not re-ask.
2. Run the 7-question representativeness gate (`representativeness.md`).
3. Follow the 10-step estimation procedure (`workflow.md`).
4. Normalize any billing-derived cost evidence (`cost-normalization.md`).
5. Obey every rule in `guardrails.md`.
6. Emit the standard output structure (defined in `workflow.md`).

## Sub-files

- `workflow.md` — the full estimation procedure, formulas, and output format.
- `representativeness.md` — the 7-question gate, 0–12 rubric, band mapping, widening rules.
- `cost-normalization.md` — turning billing/usage evidence into a clean cost contract.
- `guardrails.md` — the hard rules the estimate must always obey.
- `examples.md` — worked examples across RAG, LLM API, and batch/ETL workloads.
- `error-handling.md` — what to do when inputs are missing, contradictory, or out of scope.

## Related

This skill estimates cost *before* / *at* PoC. For **post-go-live cost optimization** (finding
orphaned resources, rightsizing, cutting waste on Azure), hand off to the Microsoft **azure-cost**
skill: https://github.com/microsoft/azure-skills/tree/main/skills/azure-cost

