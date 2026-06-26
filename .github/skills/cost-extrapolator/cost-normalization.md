# Cost Data Normalization

How to reason from measured cost data without assuming a specific vendor. Treat billing data as
**evidence, not truth**.

---

## Normalization contract

Normalize every piece of cost evidence into this contract before using it:

```text
Cost source:
- source type: manual estimate / invoice / billing query / observability metric / benchmark log / price sheet
- scope: project / resource group / service / workload / tag / account / subscription / namespace
- time window: start, end, timezone
- currency:
- cost basis: actual / amortized / list / discounted / estimated / unknown
- granularity: total / daily / hourly / per-resource / per-meter / per-operation
- included components:
- excluded components:
- known billing lag or incompleteness:
- allocation key: resource, tag, endpoint, model deployment, tenant, team, workload, job id
```

## Checks before trusting the number

### Scope contamination

Measured billing scope may include unrelated resources. If the user says "resource group cost,"
ask whether the resource group contains only the PoC workload. If not, require grouping/filtering by:
resource ID, service name, meter/category, tag, deployment name, endpoint, job ID, or environment.

### Billing lag

Recent cost data can be incomplete. If the user says "yesterday's cost," warn that recent cloud
billing can lag and may not include late-arriving meters. Label such data as **provisional** and
widen the band by one level (see `representativeness.md`).

### Actual vs amortized cost

Distinguish:

- **actual cost** — what appears on the invoice during the period;
- **amortized cost** — spreads reserved/provisioned/committed spend over usage periods;
- **list price** — undiscounted public price;
- **discounted negotiated price** — may be private and unavailable.

For extrapolation, amortized or unit-rate-based cost is usually better for unit economics. Actual
cost is useful for cashflow / invoice comparison.

### Meter grouping

Decompose measured spend by meter or service category when possible. Useful generic groupings:
compute, storage, requests, tokens, indexing, database reads/writes, network egress,
gateway/API management, observability/log ingestion, secrets/keys, orchestration/scheduler,
retries/failures.

## Token workloads (LLM)

For LLM workloads, **do not use request count alone**. Ask for or infer:

- input tokens per unit/request
- output tokens per unit/request
- cached input tokens, if applicable
- reasoning tokens, if visible
- embeddings tokens, if applicable
- model/deployment used
- batch vs online mode
- retry rate
- tool calls / retrieval calls per request

LLM-backed API unit model:

```text
cost/request =
    input_tokens/request × input_token_price
  + output_tokens/request × output_token_price
  + embedding_tokens/request × embedding_price
  + retrieval/query cost/request
  + gateway/observability cost/request
  + retry overhead
```

Document / RAG ingestion (one-time or recurring per document):

```text
ingestion cost/document =
    parse/extract
  + chunk
  + embed
  + index/write
  + graph/enrichment/classification
  + validation/evaluation
  + storage growth
```

RAG serving (per query):

```text
serving cost/query =
    retrieval
  + reranking
  + prompt tokens
  + output tokens
  + tool calls
  + logging/monitoring
```

## Pre-flight checks before a billing query

Before trusting (or even running) a billing query, confirm the environment is ready. Doing this
first avoids extrapolating from a failed, empty, or wrong-scope query.

1. **Authentication / access** — confirm you are authenticated to the right account/tenant and have
   permission to read cost data for the scope.
2. **Scope exists and is the right one** — verify the resource group / account / project / namespace
   actually exists and contains only the workload (see *Scope contamination* above).
3. **Tooling is present** — confirm the required CLI/SDK and any cost-query extension or API is
   available. If a convenience command is missing, fall back to the billing REST API.
4. **Time window is fully billed** — if the period ends recently, treat it as **provisional** (see
   *Billing lag*). A closed prior month is usually final; the current/just-ended period is not.
5. **Currency** — read the currency from the response; never assume. Do not mix currencies.
6. **Prefer decomposed output** — request a grouping (by service/meter/resource/tag) so you get a
   decomposition, not a single blob (see below).

## Cloud cost query adapter pattern (vendor-agnostic)

- A cloud cost query normally needs a **scope**, **time window**, **cost basis**, **aggregation**,
  and **grouping**.
- If the billing API can group by resource, meter, service, tag, or deployment, prefer decomposed
  cost over a single total.
- If token metrics come from observability rather than billing, join token counts to the relevant
  price sheet separately.
- If all traffic goes through an API gateway, gateway-level telemetry can be better for
  team/product chargeback than resource-level billing.

> 💡 *Illustrative only:* Azure-style workflows often separate cost (a Cost Management query by
> scope/time/aggregation), usage telemetry (Azure Monitor / Application Insights), token attribution
> (model deployment or gateway dimensions), and business allocation (tags, product IDs, subscription
> IDs, API IDs, tenant IDs). Keep such vendor references short and clearly labeled as examples — do
> not put vendor-specific commands in the main workflow.

> 💡 *Illustrative Azure recipe (one vendor among many).* The convenience command
> `az costmanagement query` is **not** always available — the `costmanagement` CLI extension ships
> only `export` / `show-operation-result`. The reliable path is the billing REST API:
>
> ```bash
> az account show                                   # 1. confirm auth + subscription
> az group show -n <rg>                             # 2. confirm scope exists
> az rest --method post \
>   --uri "https://management.azure.com/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CostManagement/query?api-version=2023-11-01" \
>   --body @query.json                              # 3. POST an ActualCost query
> ```
>
> with a body that sets `type: ActualCost`, a `Custom` timeframe, `aggregation: totalCost(Sum)`, and
> `grouping` by `ServiceName` (or `ResourceId`, `MeterCategory`, a tag, or model deployment) to get a
> decomposition. Read `Cost` and `Currency` from the returned `rows`. The same shape exists on other
> clouds via their billing/cost-explorer APIs — the principle (scope + window + basis + aggregation +
> grouping) is what transfers, not the command.

## Adapter examples (generic shapes)

- **Generic cloud billing query:** scope + time window + cost basis + group-by(meter/resource/tag).
- **Generic observability metric:** time series of requests/tokens/GB joined to a price sheet.
- **LLM token metric stream:** per-request input/output/cached/reasoning tokens per deployment.
- **API gateway chargeback stream:** per-endpoint/tenant request and token counts for allocation.
- **Batch job run log:** per-run GB processed, duration, SKU, retries, and emitted log volume.

## Cost source reliability ranking

| Evidence | Reliability |
| --- | --- |
| Production-like load test with per-component telemetry | Highest |
| Billing query grouped by resource/meter/tag plus usage metrics | High |
| Billing total for isolated workload scope | Medium |
| Billing total for shared scope | Low |
| Manual price-sheet estimate only | Medium for quote, low for measured extrapolation |
| Single smoke test with total cost only | Low |
