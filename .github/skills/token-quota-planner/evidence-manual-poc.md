# Evidence Path C — Manual PoC

Use this path when the user only has manual numbers (no deployment metrics, no telemetry). This is
**weak-to-medium** evidence; be explicit about its limits.

---

## Minimum required questions

```text
1. What was measured?
   Example: 100 requests, 20 documents, one batch run.

2. What token data is available?
   Example: average input/output, total tokens, request count only.

3. What production volume is expected?
   Example: 1M requests/day, 50K docs/day, hourly batch.

4. What peak pattern should we assume?
   Example: flat, business-hours burst, campaign burst, batch window, unknown.

5. Were the inputs/prompts representative?
   Example: toy, typical, P95/large cases.

6. Did the run include full production workflow effects?
   Example: RAG, tools, retries, cache, concurrency, streaming, long context.
```

## Rating limits

- If the user has **only request count**, assign **Low** confidence and ask for input/output token
  measurements before producing anything but a conservative template estimate.
- If prompts were toy/shorter than production, warn that average tokens likely understate P95 and
  apply the Low-rating safety multiplier (2.0×).
- If full-chain effects (RAG/tools/retries/concurrency) were not exercised, demand is understated —
  flag it and recommend a production-like measurement.

> ⚠️ Manual PoC numbers rarely capture peak-minute traffic shape. Use a conservative peak factor
> (see `demand-model.md`) and make the assumption explicit.
