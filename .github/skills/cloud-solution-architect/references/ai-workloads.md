# AI & Agentic Workload Reference

> Companion to `SKILL.md`. Use when the workload under review is a generative-AI or agentic application (LLM orchestration, Retrieval-Augmented Generation, runtime/business-editable agents). Extends the Well-Architected Framework (WAF) with the AI-specific concerns that the generic pillars do not surface on their own. Source: Azure Architecture Center — *AI workloads on Azure*, *GenAIOps*, and the *Azure OpenAI / AI Foundry baseline* architectures.

---

## 1. When to use this reference

Reach for this reference when any of the following are true:
- The system calls a Large Language Model (LLM) at runtime (chat, evaluation, summarisation, agents).
- Agent behaviour is defined in **data** (prompts, instructions, config) rather than only in code.
- Retrieval-Augmented Generation (RAG) grounds responses against a knowledge store (e.g. Azure AI Search, a vector store).
- The workload consumes a metered, quota-limited model endpoint (tokens-per-minute / requests-per-minute).

---

## 2. AI / Agentic architecture style

| Aspect | Guidance |
|---|---|
| **Topology** | Frontend → orchestration tier (agent/runner) → model endpoint(s) + retrieval (RAG) + tools. Keep orchestration stateless; externalise session/conversation state. |
| **RAG pattern** | Two common shapes: (a) **tool-based** — the model is given a search tool and decides when to retrieve; (b) **manual / server-side** — the application retrieves chunks and injects them into the prompt. Manual RAG gives control over which index/data-plane identity is used per request; tool-based reduces app code. Document the choice as an Architecture Decision Record (ADR). |
| **Agent definition** | Agents may be defined at deploy time (in code) or at runtime (from config/data store). Runtime definition maximises flexibility but couples behaviour to data that must be versioned and governed (see §3). |
| **Sequential vs parallel agents** | Parallel execution reduces latency but multiplies concurrent token demand and raises the risk of quota (429) collisions on shared deployments. Sequential execution is a legitimate, deliberate quota-protection choice — but record it as a tradeoff against latency. |

---

## 3. GenAIOps — versioning the code + config + data unit

Generative-AI systems blur the line between *code* and *configuration*. When prompts, instructions, or rubrics live outside the codebase (SharePoint, a database, blob), the deployable unit is **code + data**, not code alone.

| Concern | Why it matters | Guidance |
|---|---|---|
| **Coupling of code and behaviour-data** | A code change may assume a prompt/schema that only exists in the data store; deploying one without the other breaks the contract | Treat prompts/instructions as versioned artifacts. Promote them through Development-Test-Acceptance-Production (DTAP) **together with** the code that depends on them |
| **Behaviour drift** | If business users can edit prompts/instructions in production, the running behaviour silently diverges from what was tested and approved | Version every instruction set (content hash + author + timestamp); record the active version with each run; consider change review/approval for production edits |
| **Reproducibility** | To explain or reproduce a past output you must know the exact code version **and** the exact prompt/data/input versions in effect at that moment | Stamp each run with: code commit, prompt/instruction version, model + deployment, retrieval index version, and input-document version (see §5) |
| **Build-time evaluation decays** | Evals run only at build time lose value because production prompts can drift after release | Pair build-time evals with **online/continuous** evaluation (see §4) |

---

## 4. AI evaluation & quality

Functional tests do not tell you whether AI output is *good*. A quality system must be designed deliberately.

| Layer | Purpose | Mechanisms |
|---|---|---|
| **Offline (build-time)** | Catch regressions before release | Golden datasets, rubric-based scoring, LLM-as-judge, ground-truth comparison |
| **Online (production)** | Detect drift and real-world quality issues | Sampling + LLM-as-judge on live traffic, human-in-the-loop review, user feedback capture |
| **Rubric standardisation** | Make scores comparable across agents/domains | Shared scoring scale, required output sections, citation/grounding requirements, confidence declaration |
| **Drift-aware design** | Keep evals meaningful when prompts change | Bind eval rubrics to instruction-set versions; re-run evals when a prompt version changes |

> Self-scoring by the model alone is not an evaluation system — it has no external ground truth. Flag the absence of independent evaluation as a quality risk, especially for decision-support workloads.

---

## 5. AI observability & lineage

Generic logging/tracing is necessary but not sufficient. AI workloads need **lineage**: the ability to reconstruct the full state that produced a given output.

| Signal | What to capture |
|---|---|
| **Trace context** | Propagate W3C Trace Context across the whole run (frontend → orchestration → each model call → retrieval → tools → background tasks) so one trace ID covers the workflow |
| **GenAI spans** | Use OpenTelemetry GenAI semantic conventions: model, deployment, prompt/completion token counts, latency, finish reason |
| **Version tags** | Tag every span/log with code commit, prompt/instruction version, retrieval index version, and **input-document version** (filename alone is not a version) |
| **Token & cost metrics** | Tokens per run, TPM utilisation, cost per workflow, per-user consumption |
| **Quality metrics** | Eval scores, failure/retry rate, guardrail triggers, hallucination/citation-check results |

> Capture model, prompt version, and input version **together** — lineage is the join of all three. Without it, reproducibility in a dynamic production system is effectively impossible.

---

## 6. Token quotas & capacity management

Model endpoints are metered. Treat tokens-per-minute (TPM) and requests-per-minute (RPM) as **first-class capacity constraints**, like CPU or connection-pool limits.

### Understand the limits
- Each model **deployment** has its own TPM/RPM quota. Concurrent agents/users share it unless isolated.
- Quota is consumed by **input + output tokens**; long contexts (large RAG injections, big documents) burn quota fast.

### Handle quota exhaustion (HTTP 429)
- **Honour `Retry-After`.** On 429, back off for the duration the service specifies; do not immediately re-fire.
- **Exponential backoff + jitter**, with a bounded retry budget. Never retry-storm a throttled endpoint (see antipatterns).
- **Circuit-break** sustained throttling so callers fail fast instead of queuing unbounded work.
- **Fallback strategy** — on sustained 429, spill over to an alternate deployment/region, or downgrade to a smaller model for non-critical paths.

### Provision for capacity
| Option | When |
|---|---|
| **Pay-as-you-go / Standard** | Spiky, unpredictable, or low-volume workloads |
| **Provisioned Throughput Units (PTU)** | Predictable, latency-sensitive, high-volume workloads needing guaranteed capacity |
| **Hybrid (PTU + PAYG spillover)** | Baseline on PTU, burst to PAYG when PTU is saturated |
| **Multi-deployment / multi-region** | Spread load across deployments; route via a load balancer |

### Architect for backpressure
- Put an **AI gateway** (Azure API Management generative-AI policies) in front of model endpoints for **token-based rate limiting**, per-consumer quotas, retry, load balancing across deployments, and centralised telemetry.
- Apply **Queue-Based Load Leveling** / **Priority Queue** / **Throttling** patterns to smooth spikes and protect shared quota.
- **Reduce token demand at the source:** trim/compress context, cap `max_tokens`, paginate retrieval, and use prompt/semantic caching (e.g. Redis or a cache index) for repeated queries.
- **Plan and alert:** model peak concurrent demand against quota; alert on TPM utilisation (e.g. >80%); pre-file quota-increase requests before launch.

---

## 7. Identity & security model for AI workloads

### Principle
Prefer **workload managed identity** with **least-privilege, data-plane Role-Based Access Control (RBAC)** over service principals holding secrets. Keyless beats secret-based; narrowly-scoped beats broad.

### Decision guidance
| Resource | Preferred | Avoid / scrutinise |
|---|---|---|
| Azure AI Search, Azure OpenAI / AI Foundry, Storage | Managed identity (`DefaultAzureCredential`), keyless, with data-plane roles (e.g. *Search Index Data Reader*, *Cognitive Services User*) | API keys / connection strings in config |
| Microsoft Graph / SharePoint | Managed identity with a Graph app-role assignment, **or** a registered app using a **certificate / federated credential** in Key Vault | Client **secret** in env/config; **`Sites.Read.All`** (whole-tenant/site read) when `Sites.Selected` would do |
| Data-plane scope | Narrowest role that works; isolate sensitive data into separate services/indexes when the platform cannot scope below service level | One broad identity that can read **all** indexes / the **whole** site |

### Least-privilege blast radius
- An identity (managed identity *or* service principal) with read access to an **entire** AI Search service can read **every** index — that is the blast radius if the workload is compromised or prompt-injected. Where per-index data-plane RBAC is not available, separate sensitive indexes into their own search service or use distinct identities per sensitivity tier.
- For document stores, propagate **sensitivity labels / classification** (Microsoft Purview / Microsoft Information Protection) through retrieval into outputs, and apply the **highest** label of any source to the generated artifact. Do not treat all content as "internal" by default.

### Network & confidentiality
- For high-confidentiality targets, design **network isolation early** (private endpoints, VNet integration, no public data-plane), rather than retrofitting it. Security retrofitted onto an open baseline to reach a high classification is high-risk — shift it left, even in a Proof of Concept (PoC).

### Responsible AI guardrails
- **Prompt injection:** treat all retrieved/user content as untrusted **data**, never instructions; fence it in the system prompt; scan for known injection patterns before indexing.
- **Content safety:** layer Azure AI Content Safety on top of built-in model filters for high-sensitivity outputs; perform jailbreak/abuse testing.
- **Tool/code execution:** sandbox and review any model-generated code before execution.
- **User-facing disclaimer:** add an "AI-generated content may be incorrect" notice.

### Worked example — common pattern (illustrative)

A frequently observed split in agentic apps:
- **Azure-native services (AI Search, model/agent runtime, Storage):** workload **managed identity**, keyless, with data-plane roles (e.g. *Search Index Data Reader*). **Good pattern — keep.**
- **Microsoft Graph / SharePoint:** often a **service principal with a client secret** and a broad **`Sites.Read.All`** grant. **Opinion:** both the *mechanism* (secret) and the *scope* (whole-site read) are the weak links. Prefer managed identity (or a certificate/federated credential in Key Vault) and scope to `Sites.Selected`.
- **Search scope:** a single identity that can read the **entire** search service (all indexes). **Opinion:** acceptable for a Proof of Concept, but for production/high-confidentiality, isolate sensitive indexes or use per-tier identities to shrink the blast radius.

---

## 8. AI-specific antipatterns

| Antipattern | Problem | Fix |
|---|---|---|
| **No Evaluations** | Quality is asserted, not measured; regressions and drift go unnoticed | Offline + online evals; rubric / LLM-as-judge |
| **Prompt-as-Instruction** | Retrieved/user content is trusted as instructions → prompt injection | Fence untrusted content as data; injection scanning |
| **Token Retry Storm** | Aggressive retries on 429 deepen throttling and inflate cost | Honour `Retry-After`; backoff + jitter; circuit breaker; retry budget |
| **Unbounded Vector Store Growth** | Per-upload stores never cleaned up → quota exhaustion, cost, larger attack surface | Time-to-live (TTL), dedup by checksum, scheduled cleanup |
| **Untracked Behaviour Drift** | Editable prompts diverge from approved versions with no record | Version + stamp instruction sets; online eval |
| **Filename-as-Version** | Outputs traced only by filename, not content version | Hash/version inputs and prompts; stamp lineage on every run |

---

## 9. AI review checklist (apply alongside the WAF pillars)

- [ ] Is the deployable unit understood as **code + prompts/config + data**, and are they versioned and promoted together?
- [ ] Can a past output be **reproduced** from captured lineage (code, prompt, model, index, input versions)?
- [ ] Is there an **evaluation** mechanism (offline and online), not just self-scoring?
- [ ] Are **token/TPM quotas** modelled, monitored, and is **429** handled with backoff/fallback?
- [ ] Is identity **managed-identity + least-privilege data-plane RBAC**, with no broad secrets or whole-store read?
- [ ] Are **sensitivity labels** propagated through retrieval to outputs?
- [ ] Are **prompt-injection, content-safety, and tool-execution** guardrails in place and tested?
- [ ] Is **network isolation** designed in (not bolted on) for the target confidentiality level?

---

## Source

Azure Architecture Center — *AI workloads on Azure* and the *Well-Architected Framework* AI workload guidance; *GenAIOps*; *Azure OpenAI / AI Foundry baseline* reference architectures; Azure API Management generative-AI (AI gateway) capabilities; OpenTelemetry GenAI semantic conventions.
