# Evidence Routing

Determine which evidence path applies before estimating. Foundry usage is **deployment evidence**;
telemetry is **workload evidence**. Quota requests need both where possible.

---

## Routing table

| Evidence available | Route | Relative strength |
| --- | --- | --- |
| OpenTelemetry / application traces with token usage, latency, and request IDs | `evidence-otel-telemetry.md` | Strongest for workload-level quota planning |
| Foundry / Azure OpenAI deployment token metrics | `evidence-foundry-usage.md` | Good for deployment-level observed usage |
| Both telemetry and Foundry usage | Use both and reconcile (see below) | Best |
| Manual PoC numbers only | `evidence-manual-poc.md` | Weak to medium |
| Request count only | `evidence-manual-poc.md`, Low confidence | Weak |

## Reconciliation rule (both sources present)

```text
If both Foundry usage and telemetry exist:
- Use telemetry to estimate per-workload unit economics (tokens per business transaction).
- Use Foundry usage to validate aggregate usage and current quota pressure.
- If they disagree, DO NOT average blindly. Explain possible causes:
  - scope mismatch (deployment shared by multiple apps),
  - time-window mismatch,
  - missing model calls in telemetry (intermediate RAG/agent/tool calls),
  - retries counted on one side only,
  - cache effects,
  - telemetry sampling.
```

> 💡 If an API gateway (e.g. APIM) fronts all model calls, gateway telemetry can be the best source
> for app/team/product attribution — often better than raw model-resource metrics.

## If only Foundry usage exists (no OTel / app telemetry)

Do **not** block estimation. Proceed, but be explicit about the limits:

```text
1. Use `evidence-foundry-usage.md` to estimate from deployment-level usage.
2. Cap representativeness at Medium unless peak-minute usage, isolated deployment scope, and
   production-like traffic are ALL known.
3. Add a section from `telemetry-maturity-path.md` explaining how to get to workload-level OTel
   planning.
4. In the final report, clearly distinguish:
   - what the Foundry deployment consumed;
   - what the workload is assumed to represent;
   - what cannot be attributed without application telemetry.
```

> ⚠️ **Reconciliation rule:** Do not pretend Foundry usage is per-agent usage unless the deployment
> is isolated to one agent, or the usage can be filtered by deployment, endpoint, application, tag,
> API, tenant, or correlation ID.

## Why the distinction matters

- **Deployment evidence** answers: *"This deployment consumed X tokens and peaked at Y during the
  window."* Good for current quota pressure; weak for attributing demand to a business transaction.
- **Workload evidence** answers: *"This business transaction consumes P95 X input / Y output tokens
  across Z model calls, at A seconds latency with B retry overhead."* This is what scales cleanly to
  a target request volume.
