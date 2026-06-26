# Evidence Path B — OpenTelemetry / Application Telemetry

Use this path when the user has application-level telemetry, OpenTelemetry GenAI traces, gateway
logs, or custom token counters. This is **workload evidence** — the strongest basis for quota
planning because it ties tokens to a business transaction.

---

## Minimum required questions

```text
1. What business transaction or user journey does the telemetry represent?
   Example: answer a RAG question, summarize a document, run an agent task.

2. Do traces include all model calls in the workflow?
   Choose: all calls / most calls / final answer only / unknown.

3. What token metrics are available?
   Choose: input and output tokens / cached input tokens / reasoning tokens /
   embeddings tokens / total tokens only / request count only.

4. Do we have P50/P95/P99 token distributions?
   Choose: yes / average only / no.

5. Do we have latency, retries, throttling, cache hit rate, and concurrency?
   Choose all available.

6. What production traffic should this telemetry represent?
   Example: pilot users, all users, one app, all apps, one country, peak business process.

7. Will production use the same workflow, model, prompt version, retrieval depth, tools,
   and guardrails?
   Choose: same / partly different / unknown.
```

## Preferred telemetry fields

Map whatever is available into the normalized quota evidence contract (`quota-normalization.md`). Do
**not** depend on exact field names — OpenTelemetry GenAI semantic conventions evolve.

```text
input tokens · output tokens · cached input tokens · reasoning tokens · embedding tokens
model name · deployment name · operation name · workflow name
request ID · trace ID · span ID · streaming flag
latency · retry count · error/throttle status · cache hit/miss
tool calls · retrieval calls
```

## Strong vs weak

**Strong** when: traces map to real business transactions; **all model calls are included**; P95
token distributions are available; latency and retries are available; sampling is understood; the
sample represents production inputs and users.

**Weak** when: only final-answer calls are traced; intermediate RAG/agent/tool calls are missing;
only averages exist; telemetry is sampled without correction; prompts were toy examples; or the
production prompt/workflow differs.

> ⚠️ If traces cover only the final answer call, **fanout is missing** and demand is understated.
> Cap representativeness at Medium and ask to include RAG, tool, agent, guardrail, evaluator, and
> retry calls.

> ⚠️ If telemetry is **sampled**, ask for the sampling rate. If unknown, flag as weak evidence and
> avoid exact extrapolation.

## When upgrading from Foundry-only usage

If the prior estimate used only Foundry deployment metrics, the goal of OTel instrumentation is to
**decompose aggregate deployment usage into workload-level unit economics**. Each Foundry-only gap
maps to a specific OTel signal that closes it:

| Foundry-only gap | OTel signal that closes it |
| --- | --- |
| Which agent used the tokens? | agent id/name attributes |
| Which business process caused the peak? | workflow/operation name |
| Which request/user journey? | trace/request correlation |
| How many model calls per task? | spans per transaction |
| How large are real prompts/outputs? | P50/P95 input/output token metrics |
| How many retries? | retry/error/throttle spans or counters |
| What concurrency is needed? | P95 latency + peak RPS |
| Did cache help? | cache hit / cached token attributes |

> 🔗 For the maturity options, decision tree, and Agent Framework hosting patterns, see
> `telemetry-maturity-path.md`.
