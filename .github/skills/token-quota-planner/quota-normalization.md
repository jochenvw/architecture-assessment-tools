# Quota Normalization

Normalize quota evidence into one contract, and keep the different quota concepts distinct. Quota
terms are not interchangeable — collapsing them into a single number causes support-request
confusion.

---

## Quota evidence contract

```text
Quota evidence:
- evidence source:
- provider/platform:
- account/subscription/project:
- region:
- model:
- model version:
- deployment type:
- deployment name:
- workload/app/team:
- measured scope:
- measured period:
- current quota:
- assigned quota:
- available quota:
- observed total tokens:
- observed peak TPM:
- observed peak RPM:
- observed concurrency:
- observed latency:
- observed retry/throttle rate:
- token dimensions:
- known gaps:
```

## Keep these distinct — do not collapse into one number

| Term | Meaning |
| --- | --- |
| Current quota | What the platform shows as the present limit |
| Assigned quota | What is allocated to deployments |
| Available quota | Remaining unallocated capacity in the pool |
| Requested quota | What this report recommends asking for |
| Observed usage | What was actually measured |
| Model-level limit | Cap per model |
| Regional limit | Cap per region |
| Subscription/account/project-level limit | Cap at the billing/identity scope |
| Deployment-level allocation | TPM/RPM assigned to a specific deployment |
| TPM | Tokens per minute |
| RPM | Requests per minute |
| Concurrent requests | In-flight requests at once |
| Batch job limits | Separate limits for batch processing |
| Provisioned capacity | Reserved throughput, distinct from pay-as-you-go quota |

> ⚠️ TPM, RPM, and concurrency fail differently — always report them separately. RPM and TPM may be
> coupled on some platforms; do not assume they are independently tunable.

## Headroom check

When current quota is known, compare the recommended figure against it — an estimate that ignores the
current limit is not actionable:

```text
free            = current_limit − currently_assigned
fits_now        = recommended ≤ free
needs_increase  = recommended > free
exceeds_cap     = recommended > current_limit
```

Record `current limit`, `currently assigned`, `free headroom`, `recommended`, and the **verdict**
(fits / re-allocate / request increase / exceeds cap, with the TPM gap). On Azure, read these from
`az cognitiveservices usage list` + `account deployment list` (see `azure-foundry-notes.md`).
