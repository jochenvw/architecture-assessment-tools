# Report Template

The final output must be **top-down (Pyramid Principle, strategy-consulting style): executive answer
and recommendation first, evidence and methodology after.** Do not start with methodology. Do not
bury the recommendation. Always end with the coarse-estimate disclaimer.

> 📄 **Save this report as a Markdown file** (`token-quota-estimate-<workload-slug>-<YYYY-MM-DD>.md`)
> per the Output Contract in `SKILL.md`, then surface the executive answer and the saved path in
> chat. The file is the deliverable; the inline reply is the summary.

---

```markdown
# Token quota estimate — <workload / customer / app>

## Executive answer

Given the tokens measured on **<scope>** for **<models/deployments>** over **<period>**, and
assuming this sample represents **<representativeness assumption>**, we estimate that **<full
production load>** will require approximately:

- **<X> TPM** at peak before headroom
- **<Y> TPM** requested after applying a **<Z>× safety multiplier**
- **<A> RPM** at peak
- **<B> concurrent in-flight requests**, if latency data is available

**Verdict vs current limits:** <does this fit current quota?> — the recommended **<Y> TPM**
**<fits within / exceeds>** the current limit of **<current_limit> TPM** for **<model>** in
**<region>** (free headroom **<free> TPM**). <If it exceeds: by how much, and the action — request a
quota increase, spread across deployments/regions, or use provisioned/PTU capacity.> _(Omit if current
quota is unknown — say so.)_

Recommendation: request **<Y> TPM** for **<model>** in **<region>** under **<deployment type>**,
plus sufficient RPM/concurrency headroom for the stated peak-load pattern.

## Basis of estimate

| Item | Value | Source / assumption |
|---|---:|---|
| Measured scope | ... | ... |
| Models/deployments | ... | ... |
| Measurement period | ... | ... |
| Production load | ... | ... |
| Representativeness | Low / Medium / High | ... |
| Safety multiplier | ... | ... |

## Demand model

| Driver | Value | Source / assumption |
|---|---:|---|
| Average production RPM | ... | ... |
| Peak factor | ... | ... |
| Peak production RPM | ... | ... |
| P95 input tokens/request | ... | ... |
| P95 output tokens/request | ... | ... |
| P95 total tokens/request | ... | ... |
| Fanout / model calls per business transaction | ... | ... |
| Retry factor | ... | ... |
| Required TPM before headroom | ... | ... |
| Recommended TPM after headroom | ... | ... |
| P95 latency | ... | ... |
| Required concurrency | ... | ... |

## Quota request pack

| Field | Value |
|---|---|
| Provider/platform | ... |
| Subscription/account/project | ... |
| Region | ... |
| Model | ... |
| Model version | ... |
| Deployment type | ... |
| Deployment name | ... |
| Current quota | ... |
| Assigned quota | ... |
| Available quota | ... |
| Requested quota | ... |
| Business justification | ... |
| Risk if not approved | ... |

## Quota headroom check

Compare the recommended figure against the current limit (omit if current quota is unknown — say so).

| Metric (per model + SKU + region) | Value (TPM) |
|---|---:|
| Current limit | ... |
| Currently assigned | ... |
| Free headroom (limit − assigned) | ... |
| Required (before headroom) | ... |
| Recommended (after safety multiplier) | ... |

**Verdict:** _fits in current headroom_ / _needs re-allocation within the pool_ / _needs a
quota-increase request_ / _exceeds the model's regional cap_ — gap of **<N> TPM**. If it exceeds the
cap: spread across deployments/regions, use provisioned/PTU capacity, or request a higher limit.

## Confidence and representativeness

Rating: **Low / Medium / High**
Score: **X/12**
Safety multiplier: **X×**

Rationale: <one paragraph, direct and factual>.

## Assumptions

- ...
- ...
- ...

## Sensitivity

The estimate is most sensitive to:

1. ...
2. ...
3. ...

## Missing or weak evidence

- ...
- ...
- ...

## Path to OTel-based quota planning

<!-- Include this section ONLY when the evidence route is Foundry-only (no OTel / app telemetry).
     It must NOT replace the disclaimer. -->

Today's estimate uses Foundry deployment-level usage. This is acceptable for a coarse quota request,
but it does not fully explain per-agent or per-business-transaction demand.

Recommended path:

| Situation | Recommended next step |
|---|---|
| Agent can be hosted in Foundry | Move to Foundry-hosted Agent Framework agent and use Foundry/App Insights tracing |
| Agent must stay on Container Apps / AKS / App Service and App Insights is enough | Add Agent Framework OpenTelemetry instrumentation and export to App Insights |
| Agent must stay self-hosted but should appear in Foundry | Export OTel GenAI telemetry to the Foundry-connected App Insights resource and register as external agent |
| App only calls Foundry APIs | Keep runtime external, but add application-level OTel; Foundry API use alone does not provide workload attribution |

Target telemetry for the next estimate:
- P95 input/output tokens per business transaction
- model/deployment/region dimension
- full chain fanout
- retry/throttle rate
- cache behavior
- P95 latency under realistic concurrency

## Recommended next measurements

To tighten this estimate, measure:

1. P50/P95/P99 input and output tokens per real business transaction.
2. Peak requests/minute from realistic traffic or load test.
3. Full-chain fanout across RAG, tools, agents, guardrails, and retries.
4. P95 latency under production-like concurrency.
5. Cache hit rate, retry rate, and throttling behavior.

## Disclaimer

This is a coarse estimate for planning and quota-request preparation. It is not a vendor quote,
capacity guarantee, SLA commitment, or substitute for production load testing. Actual quota needs
may differ because of traffic shape, model behavior, prompt length, output length, retries, cache
behavior, regional capacity, deployment type, and platform-specific throttling rules.
```
