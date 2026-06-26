# Error Handling

How to respond when token evidence is missing, shared, sampled, or incomplete. Default: degrade
confidence and widen the safety multiplier rather than refusing — but never emit a bare quota number.

---

| Situation | What to do |
| --- | --- |
| **Only total tokens are known** | Compute average TPM as a **lower bound**. Apply a peak factor and Low/Medium representativeness. Warn that peak-minute usage is missing; recommend collecting it. |
| **Only request count is known** | Assign **Low** confidence. Ask for input/output token measurements. If the user insists, give a conservative template estimate with explicit assumptions. |
| **Foundry scope is shared** | Do not treat total deployment usage as workload usage unless filtered by tag, deployment, endpoint, API, application, or time window. Cap confidence at **Medium**. |
| **Telemetry is sampled** | Ask for the sampling rate. If unknown, flag as weak evidence and avoid exact extrapolation. |
| **Telemetry excludes intermediate calls** | Flag missing fanout. Cap confidence at **Medium**. Ask to include RAG, tool, agent, guardrail, evaluator, and retry calls. |
| **Missing production traffic shape** | Use conservative default peak factors: business app 5×; consumer burst 10×; unknown 10×; campaign/event 20×; batch derive from window. |
| **Missing latency** | Estimate TPM/RPM, but mark concurrency **weak**. |
| **Foundry and telemetry disagree** | Do not average. Explain likely causes (shared deployment, scope/window mismatch, missing calls, retries, cache, sampling). Use telemetry for workload, Foundry for aggregate validation. |
| **User asks for an exact quota** | Refuse exactness. Provide a coarse estimate with the disclaimer. |
| **User asks for a vendor guarantee** | Explain the skill prepares a quota request **pack**, not a guarantee of approval, availability, or SLA. |
| **Azure metric query errors or returns empty** | Don't guess metric names or scan a whole month at `PT1M`. Use the CLI recipe in `azure-foundry-notes.md`: confirm names via `list-definitions`, avoid `--query "[?...]"` under PowerShell, and drill down P1D → top days → PT1M for peak. |

> ⚠️ A bare quota number with no assumptions, representativeness rating, or safety multiplier is
> never acceptable — even on direct demand. The wide multiplier and explicit caveats *are* the
> honest answer.

## Foundry-only evidence and no OTel

```text
Proceed with a coarse estimate if minimum Foundry usage and production scale inputs are available.

Cap confidence at Medium.

If only total tokens are known, calculate average TPM as a lower bound and apply a peak factor.

Add the "Path to OTel-based quota planning" section.

Make clear that the next maturity step is workload-level telemetry, not just more billing/deployment
totals.
```

## User asks whether OTel is mandatory

```text
No. OTel is not mandatory for a coarse quota request. Foundry deployment metrics can support a
provisional estimate. But OTel or equivalent application telemetry is recommended for defensible
workload-level sizing because it captures P95 tokens, fanout, retries, latency, and
business-transaction attribution.
```

## User asks whether external-agent registration is mandatory

```text
No. External-agent registration is not mandatory for App Insights logging. It is used when a
self-hosted agent should also surface as an agent in Foundry traces/evaluations. If
App Insights/KQL/dashboards are sufficient, self-hosted OTel to App Insights may be enough.
```
