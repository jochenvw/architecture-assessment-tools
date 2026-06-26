# Demand Model

All peak-demand and quota formulas. Quota is a **peak-capacity** problem: size from peak-minute
demand and P95 tokens, never from period averages. Report TPM, RPM, and concurrency separately.

---

## Average RPM

```text
avg_rpm = requests_per_period / minutes_in_period
```

Examples:

```text
1M requests/day    = 1,000,000 / 1,440 = 694 RPM
100K requests/hour = 100,000 / 60      = 1,667 RPM
```

## Peak RPM

```text
peak_rpm = avg_rpm × peak_factor
```

Default peak factors (use measured traffic shape when available):

| Traffic pattern | Default peak factor |
| --- | ---: |
| Flat machine-to-machine | 2× |
| Business-hours enterprise app | 5× |
| Consumer / product burst | 10× |
| Campaign / event workload | 20× |
| Batch window | derive from batch duration |
| Unknown | 10× |

## Tokens per business transaction

Prefer **P95** tokens over average tokens for quota planning.

For simple online APIs:

```text
tokens_per_request =
    input_tokens + output_tokens + conversation_history_tokens
  + retrieved_context_tokens + tool_call_tokens + reasoning_tokens_if_visible
```

For RAG:

```text
tokens_per_request =
    system_prompt_tokens + user_prompt_tokens + retrieved_context_tokens
  + reranker_or_classifier_tokens + answer_output_tokens + guardrail_or_evaluator_tokens
```

For agents:

```text
tokens_per_task =
    planner_tokens + tool_selection_tokens + tool_result_context_tokens
  + intermediate_model_call_tokens + final_answer_tokens + evaluator_or_guardrail_tokens
```

For document ingestion:

```text
tokens_per_document =
    extraction_tokens + classification_tokens + chunk_summarization_tokens
  + embedding_tokens + enrichment_tokens + validation_eval_tokens
```

## Fanout

Fanout = number of model calls per business transaction.

> ⚠️ If the token measurement already includes all calls, do **not** multiply by fanout again.

```text
effective_tokens_per_business_transaction =
    sum(tokens_per_call_type × calls_per_transaction)
```

Or, if only aggregate per-transaction tokens are known:

```text
effective_tokens_per_business_transaction =
    measured_p95_total_tokens_per_transaction
```

## Retry overhead

```text
retry_factor = 1 + retry_rate
```

Defaults:

```text
known stable retry rate : use measured value
unknown online workload : 1.10
known throttling/errors : 1.20 or higher, with warning
```

## Required TPM before headroom

```text
required_peak_tpm_before_headroom =
    peak_rpm × p95_tokens_per_business_transaction × retry_factor
```

If only model-call tokens are known and fanout is separate:

```text
required_peak_tpm_before_headroom =
    peak_rpm × p95_tokens_per_model_call × fanout × retry_factor
```

## Recommended TPM (after headroom)

```text
recommended_requested_tpm =
    required_peak_tpm_before_headroom × safety_multiplier
```

Round up to sensible quota increments.

## Required RPM

```text
required_peak_rpm = peak_rpm × retry_factor
recommended_rpm   = required_peak_rpm × safety_multiplier
```

## Required concurrency

```text
peak_rps                = peak_rpm / 60
required_concurrency    = peak_rps × p95_latency_seconds
recommended_concurrency = required_concurrency × safety_multiplier
```

> ⚠️ If latency is missing, still estimate TPM/RPM but mark the concurrency figure **weak**.

## Batch workloads

Do not divide by the full day unless the batch can run all day. Use the allowed batch window:

```text
batch_units_per_minute = total_batch_units / allowed_batch_window_minutes
batch_required_tpm     = batch_units_per_minute × p95_tokens_per_unit × retry_factor
```
