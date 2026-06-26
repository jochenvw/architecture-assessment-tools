# Worked Examples

Five worked examples across the evidence paths. Numbers are illustrative but internally consistent.
Each leads with the **executive answer** (top-down), then shows the basis. See `report-template.md`
for the full report structure and `demand-model.md` for the formulas.

---

## Example A — Foundry deployment usage only

**User input**

```text
Measured scope: one Azure OpenAI / Foundry deployment "chat-prod-poc" (gpt-4.1-mini).
Period: yesterday UTC. Observed total tokens: 4,000,000. Peak-minute metrics: unavailable.
Deployment is isolated to this PoC. Target: scale pilot → full production (~10× traffic).
Production uses the same model and region.
```

**Evidence route:** Foundry observed usage (deployment evidence). **Only daily total tokens** → peak
data missing.

### Executive answer

Given **4.0M tokens** measured on the isolated **chat-prod-poc** deployment over **one day**, and
assuming the pilot is ~**10%** of production and traffic is business-hours shaped, we estimate full
production will require approximately **~153K TPM at peak before headroom** and **~215K TPM** after a
**1.4× safety multiplier**. **RPM and concurrency cannot be estimated** from this evidence (no
request count or latency). Recommendation: request **~215K TPM** (round up to the next quota
increment) for gpt-4.1-mini in the same region — and **collect minute-level TPM/RPM before
finalizing**.

### Representativeness — Medium (5/12), safety 1.4×

Token quality 1 (total only), scope isolation 2, workload realism 1, chain coverage 1, peak-shape 0,
runtime effects 0. Capped at Medium (only daily totals; no peak-minute data).

### Demand model

| Driver | Value | Source / assumption |
|---|---:|---|
| Measured avg TPM (lower bound) | 4,000,000 / 1,440 = **2,778** | daily total ÷ minutes |
| Production avg TPM (×10) | **27,780** | pilot = 10% of production |
| Peak factor | **5×** | business-hours, assumed |
| Peak TPM before retry | 138,900 | avg × peak factor |
| Retry factor | 1.10 | unknown online default |
| Required TPM before headroom | **≈153,000** | × retry |
| Recommended TPM (×1.4) | **≈215,000** | safety multiplier |

**Assumptions** — pilot is 10% of production; business-hours peak shape; same model/region/prompts.
**Sensitivity** — (1) peak factor, (2) the 10× scale assumption, (3) P95 vs average token shape.
**Missing evidence** — peak-minute TPM/RPM, request count, P95 tokens, latency.
**Next measurements** — minute-level TPM/RPM from Azure Monitor; P95 tokens; request count.

> _Disclaimer: coarse estimate for planning and quota-request preparation; not a vendor quote,
> capacity guarantee, or SLA. Daily totals are weak for quota — validate with peak-minute data._

---

## Example B — OpenTelemetry traces for a RAG assistant

**User input**

```text
Telemetry: OpenTelemetry GenAI traces. Workflow: RAG answer. Sample: 500 realistic questions.
P95 tokens — prompt/system/history: 700; retrieved context: 3,500; output: 800.
Fanout: 1.2 model calls/request. Target: 200K requests/day. Traffic: business-hours.
Retries: 5%. P95 latency: 6s.
```

**Evidence route:** OTel telemetry (workload evidence) — strongest path.

### Executive answer

Given **P95 ≈ 5,000 tokens per RAG call** across **500 realistic questions**, scaling to **200K
requests/day** on a business-hours pattern, we estimate **~4.4M TPM at peak before headroom** and
**~5.25M TPM** after a **1.2× safety multiplier**, at **~875 RPM** and **~84 concurrent requests**.
Recommendation: request **~5.25M TPM / ~875 RPM** for the RAG model+region. **Note:** this likely
exceeds a single deployment's limit and may require multiple deployments or provisioned capacity —
verify current platform limits.

### Representativeness — High (10/12), safety 1.2×

P95 tokens, isolated app telemetry, realistic sample, fanout included, retries+latency measured.
Peak shape is *estimated* (business-hours) and concurrency not directly measured — the swing factor;
treat as High-but-verify.

### Demand model

| Driver | Value | Source / assumption |
|---|---:|---|
| Avg RPM | 200,000 / 1,440 = **138.9** | requests ÷ minutes |
| Peak factor | **5×** | business-hours |
| Peak RPM | **694** | avg × peak |
| P95 tokens/call | 700 + 3,500 + 800 = **5,000** | telemetry |
| Fanout | 1.2 | model calls/request |
| Effective P95 tokens/transaction | 5,000 × 1.2 = **6,000** | tokens × fanout |
| Retry factor | 1.05 | 5% measured |
| Required TPM before headroom | 694 × 6,000 × 1.05 ≈ **4,375,000** | peak_rpm × tokens × retry |
| Recommended TPM (×1.2) | **≈5,250,000** | safety multiplier |
| Required RPM / recommended | 729 / **875** | peak_rpm × retry × 1.2 |
| P95 latency | 6 s | telemetry |
| Required / recommended concurrency | (694/60)×6 = 69.4 / **≈84** | peak_rps × latency × 1.2 |

**Assumptions** — business-hours peak; P95 stable at scale; retrieval depth unchanged.
**Sensitivity** — (1) retrieved-context tokens (3,500 dominate), (2) peak factor, (3) fanout.
**Missing evidence** — measured peak traffic profile, concurrency under load, cache hit rate.
**Next measurements** — peak RPM from a load test; concurrency under production-like load; cache rate.

> _Disclaimer: coarse estimate; not a vendor quote, capacity guarantee, or SLA. Verify model/region
> limits — required TPM may exceed a single deployment._

---

## Example C — Manual PoC API smoke test

**User input**

```text
PoC served 100 requests. Avg input 1,000 tokens, avg output 500 tokens. No P95.
No concurrency, no retries measured. Target: 1M requests/day. Traffic: business-hours enterprise app.
Prompts were shorter than production.
```

**Evidence route:** manual PoC (weak). Smoke test + no P95 → low confidence.

### Executive answer

Given a **100-request smoke test** at **~1,500 average tokens/request**, scaling to **1M
requests/day** on a business-hours pattern, we estimate **~5.7M TPM at peak before headroom** and
**~11.5M TPM** after a **2.0× safety multiplier**, at **~7,600 RPM**. **Concurrency cannot be sized
(no latency).** Recommendation: treat this as a **rough upper-planning figure only** and measure
production-like P95 tokens and latency before requesting quota — average tokens from a smoke test
materially understate P95.

### Representativeness — Low (≈2/12), safety 2.0×

Smoke test (caps Low), average tokens only, no P95, no runtime effects, prompts shorter than
production.

### Demand model

| Driver | Value | Source / assumption |
|---|---:|---|
| Avg RPM | 1,000,000 / 1,440 = **694** | requests ÷ minutes |
| Peak factor | **5×** | business-hours |
| Peak RPM | **3,472** | avg × peak |
| Avg tokens/request | 1,000 + 500 = **1,500** | PoC (no P95 — understates) |
| Retry factor | 1.10 | unknown online default |
| Required TPM before headroom | 3,472 × 1,500 × 1.10 ≈ **5,728,000** | peak_rpm × tokens × retry |
| Recommended TPM (×2.0) | **≈11,460,000** | safety multiplier |
| Required RPM / recommended | 3,819 / **≈7,640** | peak_rpm × retry × 2.0 |
| Concurrency | **weak — no latency** | latency missing |

**Assumptions** — production tokens ≈ PoC average (weak); business-hours peak; 10% retry buffer.
**Sensitivity** — (1) P95 vs average tokens, (2) peak factor, (3) retry rate.
**Missing evidence** — P95 tokens, latency, concurrency, retries, full-chain effects.
**Next measurements** — production-like P95 input/output tokens; P95 latency; retry/throttle rate.

> _Disclaimer: coarse estimate; not a vendor quote, capacity guarantee, or SLA. Smoke-test averages
> understate real demand — do not commit quota on this alone._

---

## Example D — Foundry + OTel reconciliation

**User input**

```text
Foundry deployment shows 10M tokens over one day. OTel traces for the target app show 6M tokens
over the same day. Deployment is shared by two apps. OTel sampling is 100% for the target app.
Target app expected to scale 5×.
```

**Evidence route:** both — reconcile. Use **OTel for the workload**, Foundry for **aggregate
validation**.

### Executive answer

The **10M (Foundry) vs 6M (OTel)** gap is **not** an error to average away — the deployment is
**shared by two apps**, so the other app plausibly accounts for ~4M tokens. Using the app-specific
**6M tokens/day** and a **5×** growth target, we estimate **~320K TPM at peak before headroom** after
a conservative peak factor, with a **1.4× safety multiplier**. Recommendation: size on the **OTel
6M** basis, **isolate the deployment** (or add per-app dimensions / gateway attribution), and collect
P95 tokens and latency before finalizing.

### Representativeness — Medium (capped), safety 1.4×

Shared Foundry scope (caps Medium); OTel isolated and 100%-sampled for the app, but no P95, no peak
shape, no latency.

### Demand model

| Driver | Value | Source / assumption |
|---|---:|---|
| Workload basis | **6M tokens/day** (OTel) | app-specific, 100% sampled |
| Aggregate validation | 10M tokens/day (Foundry) | shared by 2 apps — do **not** average |
| App avg TPM | 6,000,000 / 1,440 = **4,167** | daily ÷ minutes |
| Production avg TPM (×5) | **20,833** | 5× growth target |
| Peak factor | **10×** | traffic shape unknown → conservative |
| Peak TPM before retry | 208,333 | avg × peak |
| Retry factor | 1.10 | unknown online default |
| Required TPM before headroom | ≈**229,000** | × retry |
| Recommended TPM (×1.4) | ≈**320,000** | safety multiplier |

**Assumptions** — the 4M gap is the other app; 5× growth; unknown peak → 10×.
**Sensitivity** — (1) peak factor (unknown shape), (2) whether the gap is really the other app, (3)
P95 tokens.
**Missing evidence** — P95 tokens, latency, peak traffic shape, per-app deployment isolation.
**Next measurements** — isolate the deployment or add per-app/gateway dimensions; P95 tokens; peak
RPM; latency.

> _Disclaimer: coarse estimate; not a vendor quote, capacity guarantee, or SLA. Reconcile shared-
> deployment evidence before committing quota._

---

## Example E — Foundry-only usage, no OTel

**User input**

```text
Customer has one Foundry model deployment. Observed yesterday:
- total tokens: 12M
- no peak-minute TPM/RPM
- no app telemetry
- no per-agent attribution
- deployment is shared by two internal apps
Production target:
- target app expected to scale to 5× current pilot usage
- business-hours traffic pattern
- same model and region
```

**Evidence route:** Foundry observed usage, **Foundry-only mode** (no OTel). Only daily totals; shared
deployment.

### Executive answer

Given the **12M tokens** measured on the **shared** Foundry deployment over **yesterday**, and assuming
the measured usage is a rough proxy for the target app's pilot traffic, we estimate full production
will require approximately **~229K TPM at peak before headroom** and **~460K TPM** after a **2.0×
safety multiplier**. **RPM and concurrency cannot be estimated** (no request count or latency).
Recommendation: treat this as a **coarse, provisional** quota request (~460K TPM, rounded up) for the
same model/region — then **isolate the deployment or add app/agent attribution** before finalizing.

> ⚠️ Because the deployment is shared and no app-level telemetry exists, this estimate may materially
> overstate or understate the target app's true requirement — do **not** claim the full 12M tokens
> belong to the target app.

### Representativeness — Low (≈3/12), safety 2.0×

Token quality 1 (total only), scope isolation 0 (shared), workload realism 1, chain coverage 1,
peak-shape 0, runtime effects 0. Capped Low by the shared deployment **and** missing peak-minute data.

### Demand model

| Driver | Value | Source / assumption |
|---|---:|---|
| Measured avg TPM (lower bound) | 12,000,000 / 1,440 = **8,333** | daily total ÷ minutes |
| Production scale factor | **5×** | target app → 5× pilot |
| Production avg TPM | **41,667** | avg × scale |
| Peak factor | **5×** | business-hours, assumed |
| Peak TPM before retry | 208,333 | avg × peak |
| Retry factor | 1.10 | unknown online default |
| Required TPM before headroom | ≈**229,000** | × retry |
| Recommended TPM (×2.0) | ≈**460,000** | safety multiplier |
| RPM / concurrency | **unavailable** | no request count or latency |

**Assumptions** — 12M is a rough proxy for the target app (unverified; shared deployment); 5× growth;
business-hours peak; same model/region.
**Sensitivity** — (1) the target app's true share of the 12M, (2) peak factor, (3) the 5× scale.

### To tighten this estimate, measure next

| Gap | Next measurement |
| --- | --- |
| Shared deployment | Isolate deployment or add app/agent attribution |
| No peak TPM | Collect minute-level TPM/RPM |
| No per-agent usage | Add Agent Framework OTel spans with agent id/name |
| No workflow attribution | Add workflow/operation attributes |
| No concurrency | Measure P95 latency under load |
| No retry data | Log retries/throttles |

> 🔗 Include the **"Path to OTel-based quota planning"** section from `telemetry-maturity-path.md`.

> _Disclaimer: coarse, provisional estimate; not a vendor quote, capacity guarantee, or SLA. A shared
> deployment with no app telemetry cannot prove the target app's true demand — mature the telemetry
> before committing quota._
