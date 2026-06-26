# Error Handling

How to respond when inputs are missing, contradictory, or out of scope. Default behavior: ask one
concise clarifying question for a blocking gap; otherwise proceed with conservative assumptions, a
Low rating, and a wide band.

---

| Situation | What to do |
| --- | --- |
| **Missing measured cost** | Ask for the cost (with currency, scope, window). If unavailable, you cannot build unit economics — offer a price-sheet-based estimate instead and label it as a quote, not measured extrapolation. |
| **Missing measured unit count** | Ask how many units the cost covers. Without it, `variable_unit_cost` is undefined; do not invent one. |
| **Missing target volume** | Ask for the target volume and period. Without it there is nothing to scale to. |
| **Shared billing scope** | Warn about scope contamination. Require grouping/filtering (resource, tag, meter, deployment) or cap the rating at Medium. |
| **Currency mismatch** | Keep each figure in its source currency; convert only if the user gives a rate, and state the rate and date. Never silently mix currencies. |
| **Contradictory period** | Flag the contradiction (e.g., "hourly cost" vs "monthly target") and ask which is authoritative before normalizing. |
| **Cost includes unrelated resources** | Treat the total as an upper bound; ask to filter to the workload, and widen the band. |
| **User wants exact quote** | Explain this skill produces ranges, not contract prices. Offer a price-sheet estimate clearly labeled as illustrative, or route them to a vendor quote process. |
| **User wants historical forecast** | Out of scope. Explain this is bottom-up unit-economics scaling, not time-series forecasting, and route to a billing/forecasting workflow. |
| **User only has tokens, not cost** | Join token counts to a price sheet (see `cost-normalization.md`) to derive cost. Label cost basis as `list/estimated` and lower confidence accordingly. |
| **User only has cost, not usage** | You can still scale by unit count, but for LLM workloads cap representativeness at Low and ask for tokens/request. |
| **Billing query tooling/command missing** | A convenience CLI command may not exist (e.g. an extension ships without a `query` verb). Fall back to the billing REST API; if no programmatic access at all, ask the user to export the cost grouped by service/meter, or use a price-sheet estimate (labeled as such). |
| **Recent / not-yet-final period** | If the time window ends recently, label the cost **provisional**, warn about billing lag, and widen the band by one level. Prefer a closed prior period when available. |
| **User says "just give me the number"** | Produce a conservative estimate **only if minimally possible**: label representativeness **Low**, give a wide band, and state the assumptions. Still never emit a bare point estimate. |

## "Just give me the number" pattern

```text
You can have a number, but I'll give it to you honestly:

Expected: ~€X/period
Range: €low–€high (Low confidence, ±100% or wider)
Why so wide: <1–2 weak-evidence reasons>
This assumes: <2–3 conservative assumptions>
To get a tighter number, measure: <1–2 next measurements>

Indicative only — a projection from a weak sample, not a quote or budget commitment.
```

> ⚠️ A bare number with no band is never acceptable, even on direct demand. The wide band *is* the
> honest answer.
