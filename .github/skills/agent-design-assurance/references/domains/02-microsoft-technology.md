# Domain 02 — Microsoft technology stack and current capability alignment

Prefix `MT` · Build the technology inventory (`technology-inventory.json`) and compare custom implementations with **currently available** Microsoft capabilities.

## Method

1. Start from `ada.py inventory` output (`_work/repo-inventory.json`): dependency manifests, flagged AI/agent packages, preview-looking versions.
2. Confirm actual **usage** in code — an installed package is not an adopted capability.
3. For each Microsoft capability, record lifecycle (`ga`, `preview`, `deprecated`, `retired`, `unknown`) with source and verification date.
4. External verification (Microsoft Learn) only when authorised. Search with **generic product terms only** — never paste repository content, names or prompts into a query. Record `topic`, `source`, `verified_at`.
5. Roadmap, unreleased features and predictions are out of scope. Do not mention them.

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| MT-01 | Azure service inventory and responsibilities | Each Azure service used and the job it does in the solution. | IaC, `az resource list`, config |
| MT-02 | Microsoft Foundry usage | Foundry resource/project model (current vs hub-based), which Foundry capabilities are used. | IaC, SDK calls, endpoints |
| MT-03 | Agent hosting and runtime | Foundry Agent Service (prompt or hosted agents), Container Apps, Functions, App Service, AKS, or in-process harness. | IaC, Dockerfiles, agent definitions |
| MT-04 | Agent framework selection | Microsoft Agent Framework, Semantic Kernel, AutoGen, LangGraph, other, or bespoke harness; version; why chosen. | Manifests, imports, ADRs |
| MT-05 | Foundry SDKs and APIs | Which SDKs/APIs (Foundry projects SDK, OpenAI SDK, Responses/Chat Completions, Assistants) and versions. | Manifests, client construction code |
| MT-06 | Model access and inference interface | How models are reached: Foundry deployments, Azure OpenAI endpoint, gateway/APIM, direct third-party. | Client config, endpoints, IaC |
| MT-07 | Evaluation capabilities | Use of Microsoft evaluation SDK/service vs custom evaluation code. | Eval code, manifests, pipelines |
| MT-08 | Observability capabilities | Foundry observability/tracing, Azure Monitor OpenTelemetry, Application Insights usage. | Telemetry setup code, IaC |
| MT-09 | Guardrail and governance capabilities | Foundry guardrails/content filters, prompt shields, agent governance features vs custom filters. | Deployment RAI policy, middleware |
| MT-10 | Knowledge capabilities | Azure AI Search, Foundry IQ / knowledge bases, other vector stores; native vs custom retrieval. | Search client code, IaC |
| MT-11 | Third-party frameworks and services | Non-Microsoft frameworks, SaaS and models in the critical path; their role. | Manifests, endpoints |
| MT-12 | Versions, preview and deprecated dependencies | Pinned versions; preview/beta packages and APIs; deprecated APIs or models in use. | Lockfiles, api-version strings |
| MT-13 | Native vs custom implementations | Where bespoke code replicates a platform capability; what it adds or avoids. | Code, ADRs |
| MT-14 | Documented technology selection rationale | Why each major technology was chosen; alternatives rejected. | ADRs, design docs |
| MT-15 | Known product limitations and workarounds | Limitations hit (quota, region, feature gaps) and the workaround implemented. | Comments, issues, docs |

## Inventory capture

Each `technology-inventory.json` item: name, category, vendor, version + source, lifecycle + source + verified date, usage, `native_vs_custom`, rationale (or `null` with `rationale_documented: false`), limitations, workarounds, `alternatives_to_investigate` (capability, lifecycle, why, trade-offs).

## Assessment stance

- Technology-neutral: a bespoke harness can be the right answer. Capture benefits **and** costs of both options.
- Never recommend migration solely because a newer capability exists. An alternative is listed only when evidence shows a concrete gap the alternative would close.
- Preview dependencies in a production path are a fact to record with implications (support, SLA, breaking change), not an automatic defect.

## Signals → targeted questions

- Bespoke tool-calling loop alongside an installed agent framework → ask which parts of the framework are used and why the loop is custom.
- Hard-coded `api-version` in preview → ask about the upgrade path and who tracks API retirement.
- Custom content filtering → ask whether platform guardrails were evaluated and what they lacked.
