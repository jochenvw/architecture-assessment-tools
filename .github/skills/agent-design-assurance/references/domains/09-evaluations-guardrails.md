# Domain 09 — Evaluations, guardrails and behavioural assurance

Prefix `EG` · Establish evaluation maturity and how behaviour is controlled at runtime.

## Method

1. Distinguish the evaluation lifecycle explicitly: **defined** → **executed** → **passed** → **enforced as a deployment gate**. Record the highest stage proven by evidence.
2. Do not run evaluations or tests unless the user explicitly authorises it; read existing results instead.
3. For guardrails, distinguish `instructed`, `evaluated`, `enforced` and `guaranteed_by_construction` (set `assurance_level`).
4. Datasets: describe size, composition and labelling — never export dataset content.

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| EG-01 | Evaluation framework | Tools/SDKs used (Microsoft evaluation SDK/service, custom, third-party). | Eval code, manifests |
| EG-02 | Datasets and ground truth | Golden/test datasets; size; representativeness; labelling method; ownership. | Dataset metadata |
| EG-03 | Metrics and thresholds | Metrics per stage and end-to-end; acceptance thresholds; their source. | Eval config |
| EG-04 | Results and trends | Latest results, trend over versions, known failure modes. | Result files, reports |
| EG-05 | Evaluation method mix | Human vs automated; model-as-judge use and its calibration; task-specific evaluators. | Eval code |
| EG-06 | Regression and CI/CD integration | Evals run on change; gates that block release; offline vs online evaluation. | Pipelines |
| EG-07 | Trace-based and production evaluation | Evaluating from production traces; user feedback loops. | Telemetry, feedback code |
| EG-08 | Model comparison and substitution testing | Evidence used to compare models or test replacements. | Eval results |
| EG-09 | Adversarial and red-team testing | Prompt injection, jailbreak and data-exfiltration tests. | Test suites, reports |
| EG-10 | Platform safety controls | Content filters/guardrails on deployments; prompt shields; groundedness detection. | Deployment config, IaC |
| EG-11 | Prompt injection defences | Direct and **indirect** (retrieved document) injection handling; separation of instructions from data. | Code, prompts (metadata) |
| EG-12 | Tool and data-exfiltration controls | Tool allow-lists, parameter validation, outbound restrictions, sensitive-data leakage controls. | Code, network config |
| EG-13 | Input and output validation | Schema validation, policy checks, structured-output enforcement. | Code |
| EG-14 | Execution and expenditure limits | Token, cost, time and turn budgets enforced at runtime. | Code, gateway policies |
| EG-15 | Guardrail failure behaviour | Fail-open vs fail-closed; bypass paths; logging of guardrail decisions. | Code, telemetry |
| EG-16 | Evidence of control effectiveness | Tests, eval results or telemetry showing controls actually trigger. | Results, telemetry |

## Signals → targeted questions

- Eval scripts exist but no results or CI usage → ask when they were last run and what thresholds apply.
- Model-as-judge without calibration against human labels → ask how judge accuracy is known.
- Guardrail errors caught and ignored → ask whether fail-open is intentional.
