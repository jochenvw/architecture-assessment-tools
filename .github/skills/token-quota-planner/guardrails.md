# Guardrails

Hard rules every quota estimate must obey. These exist to make it **difficult to produce a
confident-looking quota request from weak token evidence**.

---

| Rule | Why |
| --- | --- |
| Never use monthly or daily average tokens alone for quota | Quota is a peak-capacity problem |
| Never emit a quota number without assumptions and a safety multiplier | Prevents false precision |
| Never rate request-count-only evidence above Low | Tokens drive quota |
| Always lead with the executive answer (top-down / Pyramid Principle) | Recommendation must not be buried |
| Always separate TPM, RPM, and concurrency | They fail differently |
| Always identify model, region, and deployment type for platform-specific requests | Quota is scoped |
| Always distinguish current, assigned, available, and requested quota | Prevents support-request confusion |
| Always check whether Foundry deployment usage is isolated or shared | Shared usage contaminates extrapolation |
| Always check whether telemetry covers the full chain | Missing RAG/agent calls understate demand |
| Always use peak traffic, not only average traffic | Throttling happens at peaks |
| Always account for retries | Failed and retried calls consume capacity |
| Always prefer P95 tokens over average tokens | Average token use understates quota needs |
| Always include a coarse-estimate disclaimer | Prevents overclaiming |
| Do not claim quota approval or capacity availability | The platform/provider controls approval |
| Do not hard-code current provider quota limits from memory | Limits change |
| Do not assume cache benefit unless measured | Cache behavior materially changes demand |
| Do not average conflicting telemetry and deployment metrics blindly | First explain the mismatch |
| If only Foundry usage exists, label it deployment-level evidence | Prevents false per-agent attribution |
| Do not treat shared deployment usage as workload usage | Prevents scope contamination |
| Do not treat Foundry API usage as Foundry observability | Runtime and observability are separate |
| Always recommend a telemetry maturity path when no OTel/app telemetry exists | Helps customer move from coarse estimate to defensible estimate |
| Do not require OTel before producing any estimate | Customers may need a provisional quota request now |
| Do not claim external-agent registration is required for App Insights logging | App Insights logging can stand alone |
| Do not claim App Insights logging alone makes the agent appear in Foundry | Foundry trace/eval visibility requires the appropriate Foundry integration/registration |

## Inline warnings and tips

> ⚠️ **Warning:** Daily total tokens are useful for cost analysis, but weak for quota planning
> unless peak-minute usage is known.

> 💡 **Tip:** If APIM or another gateway fronts all model calls, gateway telemetry can be the best
> source for app/team/product attribution.
