# Azure / Foundry Notes

Optional, platform-specific guidance for when the target platform is Azure AI Foundry / Azure
OpenAI. The main skill stays vendor-neutral; Azure specifics live here.

---

## Concepts

Azure / Foundry quota planning usually needs:

```text
subscription · region · model · deployment type · deployment name
current quota · assigned quota · available quota · TPM · RPM · concurrency (if applicable)
```

- Quota is generally scoped by **subscription, region, model, and deployment type**.
- Quota is allocated to **deployments**. Allocating TPM to one deployment reduces the available
  quota pool for that model/region/deployment type.
- **RPM and TPM may be coupled** — do not assume they are independently tunable.
- Quota is **not** tenant-wide or transferable across regions; do not assume it is.

## Evidence sources

- Model API response `usage` fields (input/output/total tokens).
- Azure Monitor model/deployment metrics (for peak-minute TPM/RPM).
- Application Insights / OpenTelemetry traces.
- APIM gateway token telemetry.
- Deployment-level metrics by model deployment name.
- Quota usage APIs or CLI.
- Load-test logs and application request logs.

> 💡 If APIM is used as an AI gateway, gateway-level telemetry can be better for app/team/product
> attribution than raw model-resource metrics.

## Querying Azure Monitor metrics (CLI recipe)

Field-tested shortcuts so the next run skips the trial-and-error. Verify metric names still exist
(`az monitor metrics list-definitions`) — they evolve — but these are the ones that matter today.

**Metric names that actually carry the signal** (Cognitive Services / Azure OpenAI accounts):

```text
TotalTokens · InputTokens · OutputTokens     → token throughput (TPM)
ModelRequests · TotalCalls                   → request count (RPM)
Latency                                       → latency (ms), Average aggregation only
```

> ⚠️ There is no out-of-the-box P95-token or P95-latency metric. `Latency` is account-average, so
> any concurrency figure derived from it is **weak**. Token-per-request is `TotalTokens / ModelRequests`
> (an **average**, not P95) — this alone caps representativeness at **Medium**.

**Step 1 — find the account that actually carries traffic.** A resource group often has several
model accounts; most are idle. Pull the period total per account and keep the one with real volume:

```powershell
$m = az monitor metrics list --resource $id --metrics TotalTokens `
     --aggregation Total --interval P1D --start-time 2026-05-01T00:00:00Z `
     --end-time 2026-06-01T00:00:00Z -o json | ConvertFrom-Json
($m.value[0].timeseries.data | Measure-Object -Property total -Sum).Sum
```

**Step 2 — drill down to the peak minute (do NOT scan the whole month at PT1M).** A full month at
`PT1M` is ~44,640 points and will be truncated/slow. Instead: get daily totals, take the top 1–2
days, then query `PT1M` **only on those days** and take the max:

```powershell
# top days
$days = $m.value[0].timeseries.data | Where-Object {$_.total -gt 0} |
        Sort-Object total -Descending | Select-Object -First 2
# peak-minute TPM on a top day
$pm = az monitor metrics list --resource $id --metrics TotalTokens `
      --aggregation Total --interval PT1M `
      --start-time 2026-05-23T00:00:00Z --end-time 2026-05-24T00:00:00Z -o json | ConvertFrom-Json
($pm.value[0].timeseries.data | Where-Object {$_.total -gt 0} | Measure-Object -Property total -Max).Maximum
```

> 💡 The busiest *minute* is often not on the busiest *day* — query PT1M on at least the top two days.

**PowerShell gotchas that cost time:**

- ❌ `--query "[?contains(name.value,'Token')]..."` — the `[?...]` JMESPath breaks PowerShell bracket
  parsing (`"] was unexpected at this time"`). ✅ Drop `--query`; pipe `-o json | ConvertFrom-Json`
  and filter with `Where-Object`.
- Pass multiple metrics space-separated: `--metrics InputTokens OutputTokens TotalTokens`.
- Empty/`$null` totals mean *no data in that bucket* (e.g. an unused account) — guard before summing.

## Azure request-pack fields

Include these in the report when Azure is the target platform:

```text
Subscription:
Region:
Model:
Model version:
Deployment type:
Deployment name:
Current quota:
Assigned quota:
Available quota:
Measured token usage:
Measured peak TPM/RPM:
Estimated production peak TPM/RPM:
Recommended requested quota:
Business justification:
Risk if not approved:
```

## Microsoft Agent Framework observability options

For Microsoft Agent Framework agents, distinguish **runtime ownership** (who runs the agent) from
**observability destination** (where telemetry lands). They are independent choices.

| Pattern | Runtime owner | Telemetry destination | Foundry trace visibility | Notes |
| --- | --- | --- | --- | --- |
| Foundry-hosted Agent Framework agent | Foundry | App Insights connected to Foundry | Native | Most managed path |
| Self-hosted Agent Framework with App Insights | Customer | App Insights / Azure Monitor | No, unless also registered | Best for normal app operations |
| Self-hosted Agent Framework registered as external agent | Customer | App Insights connected to Foundry | Yes | Hybrid: customer owns runtime, Foundry sees traces |
| Self-hosted Agent Framework using Foundry APIs | Customer | Customer choice | No, unless instrumented/registered | Using Foundry APIs is not the same as Foundry observability |

> ⚠️ Do not imply that calling Foundry models automatically makes a self-hosted agent visible in
> Foundry observability. For Foundry trace/evaluation UX, the telemetry must land in the
> Foundry-connected Application Insights resource **and** the agent must be associated correctly — for
> example through external-agent registration where applicable.

> 🔗 For the full maturity path, decision tree, and migration steps, see `telemetry-maturity-path.md`.

## Caution

> ⚠️ Do **not** hard-code current Azure model limits, quota ratios, or SKU behavior from memory —
> they change. For a real customer-facing quota request, verify current platform limits and current
> quota state from the environment (Azure Monitor, quota APIs/CLI) or official docs before
> committing numbers.
