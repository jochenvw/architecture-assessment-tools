# Worked Examples

Three worked examples across workload types. Numbers are illustrative but internally consistent.
Each is written **top-down (Pyramid Principle): the bottom-line conclusion comes first**, then the
supporting arguments, then the detail. See `workflow.md` for the canonical output format.

---

## Example A — RAG / document indexing

**User input**

```text
PoC processed 2 PDFs. Measured cost: €0.80. Target: 100 documents/week.
The two PDFs were small and clean. Only ingestion/indexing was tested;
query serving was not. Production documents will include scans, large PDFs,
and tables. Infrastructure was dev-tier.
```

### Bottom line

Assuming the measured run (2 small clean PDFs, indexing only, dev tier) is representative of
production ingestion, extrapolating to 100 documents/week leads to **~€260/month for ingestion
alone** — range **€130–€520/month (±100% or wider, Low confidence)** — **and this number excludes
query serving, storage growth, and a production index tier, which are likely to dominate the real
bill.**

Period: week (monthly equivalent in notes)

| Scenario | Recurring cost | One-time cost | Notes |
|---|---:|---:|---|
| Low | €30/week | TBD | clean-doc rate holds, no serving |
| Expected | €60/week (~€260/month) | backfill of existing corpus (unmeasured) | ingestion only; serving excluded |
| High | €120/week or more | — | scans/large/tabular docs + serving + storage baseline |

### Why this number

1. Per-doc measured = €0.80 / 2 = €0.40 on clean docs; production mix is harder, so expected per-doc
   is raised to ~€0.60 → 100 × €0.60 = €60/week.
2. Document complexity (chunks/embeddings per doc) is the dominant variable driver and is non-linear.
3. The unmeasured query-serving path and production index tier are the largest sources of
   under-estimation.

### Why this confidence

Rating: **Low — 0/12**, band **±100% or wider**. Interview: 2 small clean PDFs; indexing only;
smoke test; dev tier; serving/storage/retries untested.

| Dimension | Score |
| --- | ---: |
| Sample size (2 units) | 0 |
| Run realism (smoke) | 0 |
| Unit mix (simpler) | 0 |
| Path coverage (one path) | 0 |
| Infra realism (dev) | 0 |
| Concurrency (none) | 0 |
| **Total** | **0/12 → Low** |

Caps applied: smoke test → max Low; 1–2 units → max Medium; missing serving path → widen. For this
to hold, clean-doc economics would have to survive a much harder production document mix — unlikely.

### Cost decomposition

| Component | Fixed/Variable | One-time/Recurring | Measured? | Scaling basis | Notes |
|---|---|---|---|---|---|
| Parse + chunk + embed + index | Variable | Recurring (per doc) | Yes (clean docs only) | docs/week, but per-doc cost rises with complexity | €0.40/doc on clean small PDFs |
| Initial backfill of existing corpus | Variable | One-time | No | corpus size | Not in PoC |
| Query serving (retrieval + tokens) | Variable | Recurring | **No** | queries/period | Entirely unmeasured |
| Vector/index storage growth | Variable | Recurring | No | retained GB | Accumulates over time |
| Always-on index/db baseline | Fixed | Recurring | No (dev tier) | n/a | Production likely needs a paid tier |

**Assumptions** — serving cost excluded; dev-tier baseline ignored; no retries; linear in doc count
(optimistic).

**Missing or weak evidence** — query serving, storage growth, retries, production tier, document
complexity distribution.

**To tighten, measure next** — index a **stratified sample** (small / typical / large / ugly-scanned
docs), measure one realistic query workload, and price the production index/db tier.

_**Disclaimer — indicative only.** A projection from a 2-document PoC, not a quote or budget
commitment. Actual cost depends on the assumptions above holding in production._

---

## Example B — LLM-backed API

**User input**

```text
PoC served 100 requests. Measured cost: $0.18. Target: 1M requests/day.
Smoke test used short prompts and short outputs. No concurrency test.
No cache behavior measured. No retries measured. Production will use longer
user conversations.
```

### Bottom line

Assuming the measured smoke test (100 short-prompt requests) is representative of production
conversations, naively extrapolating to 1M requests/day lands near **~$1,800/day (~$54k/month)** —
range **$900–$5,400/day (±100% or wider, Low confidence)** — **but request count alone cannot carry
this estimate: production conversations are longer and no token, cache, or retry data was measured.**

Period: day

| Scenario | Recurring cost | One-time cost | Notes |
|---|---:|---:|---|
| Low | ~$900/day | — | short outputs hold, high cache hit |
| Expected | ~$1,800/day | — | naive scale ($0.0018/req); longer convos offset by caching (assumed) |
| High | ~$5,400/day or more | — | long outputs, retries, no cache, gateway/log overhead |

### Why this number

1. Output tokens per request are the dominant driver and grow with task complexity — not measured.
2. Cache hit rate could halve or double the bill — not measured.
3. Retries and rate-limit-driven parallel deployments add overhead — not measured.

The expected figure is a **blob fallback**: $0.18 / 100 = $0.0018/req → 1M/day × $0.0018 =
$1,800/day. It is a naive scale, flagged low-confidence because token mix is unknown.

### Why this confidence

Rating: **Low — ~1/12**, band **±100% or wider**. Interview: smoke test; short prompts/outputs
(simpler than production); serving path only; no concurrency, cache, or retry data; request count
known but **no token data**. An LLM workload with only request count is capped at Low — request
count alone is insufficient, and production "longer conversations" make the smoke test optimistic.

### Cost decomposition

| Component | Fixed/Variable | One-time/Recurring | Measured? | Scaling basis | Notes |
|---|---|---|---|---|---|
| Input tokens | Variable | Recurring | No (only request count) | input tokens/req | Drives cost; longer convos increase it |
| Output tokens | Variable | Recurring | No | output tokens/req | Grows with task complexity, non-linear |
| Retrieval / tool calls | Variable | Recurring | No | calls/req | Unknown |
| Retries / failures | Variable | Recurring | No | retry rate | Unmeasured overhead |
| Gateway + logging | Mixed | Recurring | No | req volume × verbosity | Scales with traffic |
| Min provisioned capacity / replicas | Fixed | Recurring | No | n/a | Rate limits may force parallel SKUs |

**Assumptions** — token mix similar to smoke test (weak); no concurrency premium; cache neutral;
retries negligible. All doubtful.

**Missing or weak evidence** — tokens per request, cache behavior, retries, concurrency, gateway and
log ingestion cost.

**To tighten, measure next** — capture **input/output tokens per request** on realistic
conversations, run a concurrency/rate-limit test, and measure cache hit rate and retry overhead.

_**Disclaimer — indicative only.** A blob-fallback projection from a 100-request smoke test, not a
quote or budget commitment. Actual cost depends on the assumptions above holding in production._

---

## Example C — Batch / ETL

**User input**

```text
One sample ETL run processed 10GB and cost £3.20. Target: hourly production run.
Production average input is 25GB/run, with 90-day retention. Same architecture
but smaller SKU in PoC. Logs are verbose.
```

### Bottom line

Assuming the measured 10GB run is representative of per-GB processing cost on production-equivalent
architecture, extrapolating to hourly 25GB runs leads to **~£6,400/month** — range
**£3,500–£9,000/month (±40%, Medium confidence)** — **assuming the smaller PoC SKU does not hit a
step change at 25GB, and excluding separately-metered log ingestion and 90-day retained storage.**

Period: month (730 runs/month = 24 × 30.4)

| Scenario | Recurring cost | One-time cost | Notes |
|---|---:|---:|---|
| Low | ~£3,500/month | — | per-GB rate holds, modest logs/storage |
| Expected | ~£6,400/month (£5,840 compute + ~£600 storage/logs) | initial backfill if any | ±40% band |
| High | ~£9,000/month or more | — | SKU step change at 25GB, verbose log ingestion, full 900GB retained |

### Why this number

1. Cost scales by **GB processed, not run count**: £3.20 / 10GB = £0.32/GB → 25GB × £0.32 = £8.00/run
   → 730 runs × £8.00 = £5,840/month compute.
2. A SKU step change at the larger 25GB input could break the per-GB linearity upward.
3. Verbose log ingestion and 90-day retained storage (~900GB steady-state) add recurring cost not
   isolated in the PoC.

### Why this confidence

Rating: **Medium — 5/12**, band **±40%** (capped at Medium because production uses a different SKU).
Interview: one realistic run (not a smoke test); same architecture, smaller SKU; realistic-ish data
volume; storage growth and log ingestion not separately measured; no concurrency concern (sequential
hourly batch).

| Dimension | Score |
| --- | ---: |
| Sample size (1 realistic run) | 1 |
| Run realism (partial realistic) | 1 |
| Unit mix (plausibly typical) | 1 |
| Path coverage (compute yes; storage/logs no) | 1 |
| Infra realism (same arch, smaller SKU) | 1 |
| Concurrency (n/a for sequential batch) | 0 |
| **Total** | **5/12 → Medium** |

### Cost decomposition

| Component | Fixed/Variable | One-time/Recurring | Measured? | Scaling basis | Notes |
|---|---|---|---|---|---|
| Compute per run | Variable | Recurring | Yes (10GB run) | GB processed | £3.20 / 10GB = £0.32/GB |
| Storage accumulation | Variable | Recurring | No | retained GB | 90-day retention compounds |
| Log ingestion | Variable | Recurring | No | run volume × verbosity | Verbose logs flagged |
| Larger SKU step | Fixed/step | Recurring | No | tier breakpoint | 25GB may need bigger SKU |

**Assumptions** — cost scales linearly with GB at £0.32/GB; same SKU handles 25GB (risk: step
change); storage ≈ 900GB steady-state (10–25GB/day × 90 days); logs estimated.

**Missing or weak evidence** — production-SKU compute cost, separate storage and log meters.

**To tighten, measure next** — run **one production-sized (25GB) batch on the production SKU** and
measure compute, log ingestion, and storage growth as separate meters.

_**Disclaimer — indicative only.** A projection from a single 10GB PoC run on a smaller SKU, not a
quote or budget commitment. Actual cost depends on the assumptions above holding in production._
