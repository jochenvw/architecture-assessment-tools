# Representativeness Gate

The representativeness gate decides how much to trust the measured sample. It controls the **width
of the confidence band**, not the point estimate.

Keep the gate small and concrete. Ask at most **7 required questions** before estimating, unless the
user explicitly asks for a deep analysis. If the user already provided enough information, do not
re-ask — score from the facts. If the user refuses or cannot answer, continue with conservative
assumptions and assign a **Low** representativeness rating.

---

## The 7-question gate (copy-runnable)

```text
To estimate this responsibly, answer these 7 items:

1. What was measured?
   Example: 2 documents processed, 100 API calls, one batch run.

2. What was the measured cost?
   Include currency, time window, and what was included.
   Example: €0.42 for the indexing run only; serving/querying not included.

3. What production volume should we estimate?
   Example: 100 docs/week, 1M requests/day, hourly batch.

4. Was the PoC run a smoke test or a realistic run?
   Choose: smoke test / partial realistic run / representative load test.

5. Were the measured units typical of production?
   Choose: simpler than production / roughly typical / included small, typical, and large cases.

6. Did the PoC exercise all important paths?
   Choose any that apply:
   - one-time setup/provisioning
   - ingestion/indexing
   - serving/querying
   - storage growth
   - reprocessing/retries
   - egress/networking
   - monitoring/logging
   - none/unknown

7. Was the PoC infrastructure equivalent to production?
   Choose: dev/free/shared tier / smaller but same architecture / production-like SKU and concurrency.
```

## Scoring rubric (0–12)

Six dimensions, each scored 0, 1, or 2.

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Sample size | 1–2 units or single run | small but non-trivial sample | load test or statistically useful sample |
| Run realism | smoke test / manual kicking tires | partial realistic run | representative steady-state/load test |
| Unit mix | clearly simpler than production | plausibly typical | includes small/medium/large or P50/P95 cases |
| Path coverage | only one path exercised | major path exercised, some missing | setup + recurring paths covered |
| Infrastructure realism | free/dev/shared tier | same architecture, smaller scale | production-like SKU/config/concurrency |
| Concurrency/batching | absent or unknown | partially tested | production-like concurrency/rate/batching |

## Score → rating → default band

| Score | Rating | Default band |
| ---: | --- | ---: |
| 0–4 | Low | ±100% or wider |
| 5–8 | Medium | ±40% |
| 9–12 | High | ±15% |

These are heuristics. They are visible and configurable here on purpose — adjust them if a workload
or organization has a better-calibrated mapping, but state any change in the estimate output.

> 💡 The rating changes the **band width**, not the point estimate. A Low rating on a €5,000/month
> estimate means €2,500 / €5,000 / €10,000, not a different expected value.

```text
Point estimate: €5,000/month
Low representativeness band ±100%:
  Low scenario:  €2,500/month
  Expected:      €5,000/month
  High scenario: €10,000/month
```

## Band-widening rules (caps and downgrades)

Apply these after scoring. They can cap the rating or widen the band beyond the default.

- If sample size is 1–2 units: rating **cannot exceed Medium**.
- If only a smoke test was run: rating **cannot exceed Low**.
- If production uses a different pricing mode or SKU: rating **cannot exceed Medium**.
- If major paths were not exercised: **widen the band by at least one level**.
- If the workload is LLM-heavy and only request count is known (no tokens): rating **cannot exceed
  Low**.
- If billing data is from a very recent period and may be incomplete: label as **provisional** and
  **widen by one level**.
- If cost scope may contain unrelated resources: rating **cannot exceed Medium** unless
  filtered/grouped.

If important unmeasured paths exist, prefer adding explicit line-item assumptions over hiding the
uncertainty inside a symmetric band.

## Worked rating examples

**Low (score 0–4).** PoC processed 2 clean PDFs, indexing only, dev tier, query path untested.
Sample size 0, run realism 0, unit mix 0, path coverage 0, infra 0, concurrency 0 → **0/12, Low,
±100% or wider**. Capped at Low anyway (smoke test + 1–2 units).

**Medium (score 5–8).** One production-architecture ETL run on a smaller SKU, realistic 10GB input,
verbose logs, no concurrency test. Sample size 1, run realism 1, unit mix 1, path coverage 1,
infra 1, concurrency 0 → **5/12, Medium, ±40%**. Capped at Medium (different SKU).

**High (score 9–12).** Production-like load test with mixed P50/P95 inputs, all recurring paths
exercised, production SKU and concurrency, per-component telemetry. Most dimensions 2 → **10/12,
High, ±15%**.
