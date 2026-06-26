# Evidence Path A — Foundry / Azure OpenAI Observed Usage

Use this path when the user has, or can query, usage from a Foundry / Azure OpenAI deployment. This
is **deployment evidence**: strong for current quota pressure, weaker for attributing demand to a
business transaction.

---

## Minimum required questions

```text
1. What is the measured scope?
   Example: subscription, resource group, Foundry project, Azure OpenAI resource,
   model deployment, APIM gateway, application tag.

2. Which model deployments are included?
   Example: gpt-4.1-mini deployment A, embedding deployment B.

3. What period was measured?
   Example: yesterday UTC, 2026-06-25 00:00–23:59, one-hour load test.

4. Is the measured scope isolated to this workload?
   Choose: isolated / shared / unknown.

5. Do we have peak-minute metrics or only total tokens over the period?
   Choose: peak TPM/RPM available / hourly totals / daily total only / unknown.

6. What production load should this represent?
   Example: 10% pilot, one business process, one country, one app team,
   full production equivalent, smoke test only.

7. Will production use the same model, region, deployment type, prompt shape, and gateway path?
   Choose: same / partly different / unknown.
```

## Risks to emphasize

- **Scope contamination** — shared resource groups / deployments include unrelated usage.
- **Average-vs-peak** — totals hide the peak minute that actually drives quota.
- **Shared deployment** — usage is not attributable to one workload without filtering.
- **Missing business-transaction attribution** — tokens are not tied to a unit of work.
- **Missing P95 token distribution** — averages understate peaks.
- **Regional / model / deployment-type specificity** — quota is scoped; production must match.

## Strong vs weak

**Strong** when: the deployment is isolated; the window is representative; **peak-minute TPM/RPM is
available**; all production paths use the measured deployments; same model, region, deployment type,
and prompts will be used.

**Weak** when: only daily total tokens are known; the deployment is shared; the period was a smoke
test; traffic was unrepresentative; or production uses different models, regions, or deployment
types.

## Output of this path

```text
Measured deployment usage:
- scope:
- models/deployments:
- measured period:
- total input tokens:
- total output tokens:
- total tokens:
- peak TPM:
- peak RPM:
- measured concurrency if available:
- throttling/errors if available:
- current quota if available:
- representativeness assumption:
```

## When only total tokens are available

Compute average TPM **as a lower bound only**:

```text
average_tpm = total_tokens / measured_minutes
```

> ⚠️ Average TPM is a **lower bound** for quota planning. Quota must be based on peak-minute demand,
> not the period average. Recommend collecting minute-level TPM/RPM (e.g. Azure Monitor metrics) and
> cap representativeness at Medium until peak data exists.

For Azure-specific evidence sources and request-pack fields, see `azure-foundry-notes.md`.

---

## Foundry-only evidence mode

Use this mode when the user has deployment-level Foundry / Azure OpenAI token usage but **no**
OpenTelemetry, traces, Application Insights agent telemetry, APIM token attribution, or
application-level counters.

Still produce a coarse estimate — but surface the telemetry gap and recommend a path forward. Ask
these minimum questions (score from what the user already gave; do not re-ask):

```text
1. What Foundry scope was measured?
   Example: project, Azure OpenAI resource, deployment, model, APIM gateway, subscription, resource group.

2. Which models/deployments are included?
   Example: chat model, embedding model, reranker, evaluator.

3. What period was measured?
   Example: yesterday UTC, one-hour test, seven-day pilot.

4. Was the measured scope isolated to one agent/workload?
   Choose: isolated / shared / unknown.

5. Do we have peak-minute TPM/RPM or only total tokens?
   Choose: peak-minute available / hourly totals / daily total / unknown.

6. What does the measured period represent?
   Example: smoke test, one pilot team, 10% load, one country, full production-like traffic.

7. What does full production look like?
   Example: 10× users, 1M requests/day, all countries, all business processes.
```

## What Foundry-only usage can and cannot prove

| Evidence | Can support | Cannot reliably prove without telemetry |
|---|---|---|
| Deployment total tokens | Aggregate deployment usage | Per-agent or per-user-journey usage |
| Peak TPM/RPM | Capacity pressure on deployment | Which workflow caused the peak |
| Model/deployment dimension | Model-specific demand | Business transaction unit economics |
| Current quota usage | Current quota pressure | Required quota for future workload mix |
| Total tokens over period | Coarse scaling input | Peak capacity unless peak-minute data exists |

> ⚠️ Foundry-only usage is **deployment-level evidence**. It is useful for coarse quota sizing, but
> weak for workload-level planning unless the deployment is isolated and peak-minute usage is
> available.

If only daily/monthly total tokens are known, calculate average TPM **as a lower bound only**, then
apply a peak factor before recommending quota:

```text
average_tpm_lower_bound = total_tokens / measured_minutes

estimated_peak_tpm =
    average_tpm_lower_bound
  × production_scale_factor
  × peak_factor
  × retry_factor

recommended_requested_tpm =
    estimated_peak_tpm
  × safety_multiplier
```

> 🔗 **Required handoff:** After producing the Foundry-only estimate, include the
> **"Path to OTel-based quota planning"** section from `telemetry-maturity-path.md`. The next maturity
> step is workload-level telemetry — not just more billing/deployment totals.
