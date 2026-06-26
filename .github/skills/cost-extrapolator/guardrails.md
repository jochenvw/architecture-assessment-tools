# Guardrails

Hard rules every estimate must obey. These exist to make it **difficult to produce a
confident-looking cost estimate from a weak PoC sample**.

---

| Rule | Why |
| --- | --- |
| Never emit a single point estimate without a band | Prevents false precision |
| Always lead with the answer (top-down / Pyramid Principle) | Conclusion + key caveat must come before any table |
| Always close with an "indicative only" disclaimer | Estimate is a projection, not a quote or budget commitment |
| Never scale a single-unit sample as High confidence | Sample is too weak |
| Always separate one-time and recurring cost | Prevents onboarding cost from polluting run-rate |
| Always separate fixed and variable cost | Prevents wrong unit economics |
| Always list unmeasured paths | Prevents hidden omissions |
| Always surface assumptions | Makes uncertainty auditable |
| Do not treat recent billing data as final | Billing data can lag |
| Do not treat request count as enough for LLM workloads | Token mix drives cost |
| Do not treat dev/free tier as production-linear | Production often has minimum SKUs and step changes |
| Do not silently use vendor price sheets as measured cost | Quoted price is not observed workload behavior |
| Do not use historical trend forecasting | This skill is bottom-up scaling, not time-series forecasting |

## Inline warnings and tips

> ⚠️ **No bare numbers.** A response like `€4,812.37/month` with no band, no assumptions, and no
> representativeness rating is a guardrail violation. Always wrap it in the output structure from
> `workflow.md`.

> ⚠️ **Avoid false precision.** Prefer `Expected €4,800/month, range €2,900–€8,600` over a number
> with cents. Round to the precision your evidence justifies.

> ⚠️ **One-time vs recurring.** Never roll initial indexing, backfill, or fine-tuning into the
> monthly run-rate. If you amortize, state the amortization period explicitly.

> 💡 **Let representativeness do the work.** When evidence is weak, do not refuse — widen the band,
> drop the rating, and clearly say what to measure next.

> 💡 **Name the dominant drivers.** Every estimate should state the 2–3 cost drivers it is most
> sensitive to, so the reader knows where the risk concentrates.

> 💡 **Token mix over request count.** For any LLM-backed workload, request count alone caps
> representativeness at Low. Push for input/output tokens, cache behavior, and retries.
