# Estimation Workflow

The full estimation procedure. Run it in order. Do not skip the representativeness gate.

---

## Estimation procedure (10 steps)

1. **Normalize input.** Collect the required inputs (see `SKILL.md`). If the cost came from a
   billing system, run the **pre-flight checks** in `cost-normalization.md` first (auth, scope
   exists, tooling present, period fully billed, currency, prefer decomposed/grouped output), then
   normalize it. Confirm currency, scope, and time window.
2. **Run representativeness gate.** Ask the 7 questions in `representativeness.md` (or score from
   facts the user already provided). Produce a 0–12 score, a rating, and a band width.
3. **Decompose measured cost.** Classify every cost driver as fixed/variable and one-time/recurring
   (see "Cost decomposition" below). If the cost is an undecomposable blob, say so.
4. **Identify missing cost paths.** List paths the PoC did not exercise (setup, ingestion, serving,
   storage growth, retries, egress, monitoring). Missing paths widen the band or add line-item
   assumptions.
5. **Build the unit model.** Derive `variable_unit_cost` and isolate the fixed baseline. For LLM
   workloads, build the token-level unit model (see `cost-normalization.md`).
6. **Translate target volume into a period.** Convert the target into a consistent period (day /
   week / month). Account for storage accumulation and retention.
7. **Apply fixed + variable + one-time formulas.** See "Formulas" below.
8. **Apply confidence band from representativeness.** The band width comes from the rating, widened
   by any rules in `representativeness.md`. The band changes only the low/high scenarios, never the
   expected point estimate.
9. **Produce scenarios.** Low, Expected, High — recurring and one-time reported separately.
10. **State assumptions and next measurements.** List assumptions, sensitivities, weak evidence, and
    what to measure next to tighten the estimate.
11. **Write it top-down.** Present the report answer-first (Pyramid Principle): the bottom-line
    conclusion sentence and scenario table come before any supporting detail (see "Output format").

## Cost decomposition before scaling

Classify each cost driver on two axes.

**Fixed / baseline** — exist even at low traffic: minimum SKU, provisioned capacity, always-on
VM/container, database baseline, gateway baseline, monitoring workspace.

**Variable / per-unit** — scale with volume: requests, tokens, documents, GB processed, CPU
seconds, rows processed, function executions.

**One-time** — incurred during onboarding/setup: migration, initial indexing, model fine-tuning,
backfill, provisioning.

**Recurring** — incurred every period: serving, queries, storage growth, retention, observability,
network egress, recurring batch compute.

> ⚠️ Report one-time and recurring costs separately. Never mix one-time onboarding cost into the
> steady-state recurring bill unless explicitly amortizing it — and if you amortize, state the
> amortization period.

## Formulas

```text
variable_unit_cost = measured_variable_cost / measured_units

expected_recurring_cost =
    fixed_baseline_per_period
  + variable_unit_cost × target_units_per_period
  + accumulated_storage_cost
  + retry_overhead
  + observability_overhead
```

Band scenarios from representativeness (band = ±Y%):

```text
low_scenario      = expected_recurring_cost × (1 − Y/100)
expected_scenario = expected_recurring_cost
high_scenario     = expected_recurring_cost × (1 + Y/100)
```

If important unmeasured paths exist, widen the band or add explicit line-item assumptions instead of
relying on the symmetric band alone.

### Blob fallback (last resort)

If measured cost cannot be decomposed at all:

```text
expected_cost = measured_cost × scale_factor
```

Only allowed with **all** of:

- Low or Medium confidence (never High);
- an explicit warning that this is a naive scale;
- stated assumptions;
- a recommendation to measure decomposed components.

## Volume model

Translate the target volume into a cost period. Examples:

```text
100 documents/week         → recurring weekly cost and monthly equivalent
1M requests/day            → daily and monthly recurring cost
hourly batch               → 24 runs/day × 30.4 days/month ≈ 730 runs/month
10GB/day growth, 90-day retention → steady-state retained ≈ 900GB
```

### Stated load fraction ("the measured period is X% of normal load")

Users often give the target as a **fraction of normal load** rather than an absolute volume, e.g.
"May was 20% of a normal month." Convert it to a scale factor and apply it **only to variable
components** — fixed baseline costs do not scale:

```text
scale_factor       = 1 / load_fraction            # 20% → ×5
expected_recurring = fixed_baseline + variable_cost × scale_factor
```

> ⚠️ A stated load fraction is **user-asserted, not measured**. Record it as a top-line assumption
> *and* a primary sensitivity, and never let it silently multiply the fixed baseline. Applying the
> factor to the whole bill (`total × scale_factor`) is the naive-scale failure mode — it overstates
> cost because fixed components (security plans, registries, always-on baselines) do not grow with
> load.

The model must handle: throughput, per-unit variable cost, fixed baseline, storage/state
accumulation, retention, reprocessing/re-indexing, retry/failure rate, growth curve (if given),
concurrency and batching effects, and tier breakpoints / minimum SKUs.

Always separate:

```text
One-time onboarding cost
Steady-state recurring cost per period
Ramp-up cost (only if a growth curve is given)
```

## Non-linearity and step functions

Explicitly look for and list non-linear drivers in the output:

- LLM output tokens grow with task complexity, not just request count.
- Larger documents create disproportionately more chunks, embeddings, prompts, retrieval calls.
- Storage accumulates over time.
- Log ingestion scales with request volume and verbosity.
- Batch workloads may cross into larger compute tiers.
- API services may need minimum provisioned capacity, replicas, gateways, or databases.
- Provisioned throughput can create step changes.
- Free/dev tiers may disappear in production.
- Rate limits may force parallel deployments or higher SKUs.
- Caching can make smoke tests understate uncached production cost.
- Retries and failures can materially increase cost.

## Output format

Write the estimate **top-down (Pyramid Principle, McKinsey style): answer first, then support, then
detail.** The reader must get the conclusion and its key caveat in the first two sentences, before
any table. Never hide assumptions in prose. Never produce only a point estimate.

Order of the report:

1. **Bottom line** — the governing conclusion sentence + the scenario table.
2. **Why this number** — the 2–3 supporting arguments (dominant drivers, key load assumption).
3. **Why this confidence** — the representativeness rating that sets the band width.
4. **Detail** — decomposition, full assumptions, sensitivity, weak evidence, next measurements.

Every completed estimate must use this structure:

```markdown
## Bottom line

Assuming the measured period **[start–end]** and the cost incurred over **[scope]** are
representative of **[production behavior, e.g. steady-state serving load]**, extrapolating to
**[target volume]** leads to **~[expected]/[period]** — range **[low]–[high] ([±Y%], [Low/Medium/High]
confidence)** — assuming **[the single most load-bearing assumption, e.g. token mix and concurrency
hold]**.

Period: [day/week/month/etc.]

| Scenario | Recurring cost | One-time cost | Notes |
|---|---:|---:|---|
| Low | ... | ... | ... |
| Expected | ... | ... | ... |
| High | ... | ... | ... |

## Why this number

The estimate is driven mainly by:
1. ...
2. ...
3. ...

## Why this confidence

Rating: Low / Medium / High
Score: X/12
Band used: ±Y%
Justification: one sentence (what would have to be true for this to hold).

## Cost decomposition

| Component | Fixed/Variable | One-time/Recurring | Measured? | Scaling basis | Notes |
|---|---|---|---|---|---|

## Assumptions

- ...

## Missing or weak evidence

- ...

## To tighten this estimate, measure next

- ...

## After go-live: optimize cost

Once the workload is in production, shift from *estimating* to *reducing* spend. Use the Microsoft
**azure-cost** skill's cost-optimization workflow to find orphaned resources, rightsize, and cut
waste:
- Repo: https://github.com/microsoft/azure-skills
- Skill: https://github.com/microsoft/azure-skills/tree/main/skills/azure-cost

---

_**Disclaimer — indicative only.** This is a scaled projection from a small measured proof-of-concept
sample, not a quote, budget commitment, or guarantee of actual cost. The figures hold only insofar as
the assumptions and representativeness above hold in production; real spend will vary with workload
mix, volume, pricing changes, and unmeasured paths. Validate against a production-like load test
before committing budget._
```
