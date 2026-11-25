# agent-design-assurance

Read-only, evidence-first **discovery** for Azure agentic AI applications. It produces a sanitised,
portable evidence package that an independent architect can review **without access to the
repository or Azure**. It is the input to a design assurance review, not the review itself.

## 1. What you get

| Output | Purpose |
|---|---|
| `discovery-report.md`, `executive-discovery-summary.md` | Narrative across 12 domains |
| `architecture.json`, `execution-flows.json` | Graph and flows for 9 diagram views |
| `evidence.json`, `assessment.json` (+ CSVs) | Evidence, per-criterion status, maturity, confidence, coverage, observations |
| `open-questions.md` | Prioritised, evidence-anchored questions |
| `technology-inventory.json`, `workload-characteristics.json`, `design-decisions.json` | Stack, volumes, decisions |
| `azure-configuration.json` | Optional deployed configuration, aliased |
| `manifest.json`, `discovery-coverage.json` | Scope, provenance, sanitisation, coverage |
| `_dist/*.zip` + `.sha256` | Handover archive (never uploaded) |

The full layout is in `references/output-package.md`. A synthetic, gate-clean example is in
`examples/contoso-claims-review/`.

## 2. Install

| Need | Detail |
|---|---|
| Python | 3.10+; **stdlib only**, nothing to `pip install` |
| Git | Optional; enables revision capture and the repository-unchanged gate |
| Azure CLI | Optional; only for Azure discovery, already logged in. Never installed by the skill |

Install (see the root `README.md`):

```bash
copilot plugin install jochenvw/architecture-assessment-tools   # Copilot CLI: /aztools:agent-design-assurance
```

No Copilot CLI, or only this skill? Copy it with git:

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/jochenvw/architecture-assessment-tools aztools-tmp
git -C aztools-tmp sparse-checkout set .github/skills/agent-design-assurance
# copy aztools-tmp/.github/skills/agent-design-assurance to .github/skills/ (or ~/.copilot/skills/)
```

## 3. Invoke

Ask your coding agent, for example:

> Run the agent-design-assurance skill against this repository using the Azure agent, <platform> and
> <workload> profiles. Produce a sanitised, self-contained design assurance discovery package for
> independent architectural review.

**The only question you will be asked:** "May I use the Azure CLI to read the deployed
configuration and usage telemetry (read-only)?"

| Answer | What happens |
|---|---|
| Yes | The agent finds the subscriptions and resource groups itself (`.azure/*/.env`, IaC, `az group list`) and reads configuration plus aggregated Application Insights telemetry. Nothing is changed. |
| No | Repository only. Deployed-state criteria stay unknown, and the gap is recorded. |

Everything else is fixed. Scope is always the whole solution, from agent to infrastructure. Profiles
come from your invocation. Business context is derived from the repository; gaps become open
questions in the package. Anonymisation is always on: repository, organisation, subscription,
resource-group and resource names are replaced by aliases (`APP-1`, `AZ-RG-1`, ...) so the receiver
cannot derive internals. See [`references/discovery-methodology.md`](references/discovery-methodology.md) §1.

The agent follows `SKILL.md`. The CLI can also be driven directly:

```bash
S=.github/skills/agent-design-assurance/scripts/ada.py
python $S profiles                                                     # list
python $S init --repo . --out design-assurance-output --profiles azure-agent,example-platform
python $S criteria --out design-assurance-output --domain 06           # per-domain worklist
# … agent investigates and edits the JSON / Markdown files …
python $S alias    --out design-assurance-output --term "<product name>" --kind SYSTEM   # extra internal names
python $S render   --out design-assurance-output
python $S sanitize --out design-assurance-output --apply
python $S check    --out design-assurance-output
python $S package  --out design-assurance-output
```

Azure discovery, after a "yes" (one run per resource group; telemetry is included):

```bash
python $S azure collect --out design-assurance-output --subscription <id> --resource-group <rg> \
                        --environment test --execute       # add --skip-telemetry to omit telemetry
```

Exit codes: `0` success, `1` gate or sanitise failures, `2` usage, scope or profile errors, or Azure
not reachable.

## 4. Configure: profiles

| Kind | Example | Adds |
|---|---|---|
| generic (required) | `azure-agent` | 12 domain catalogues (172 criteria) |
| platform | `example-platform` | Customer platform standard criteria |
| workload | `example-document-review` | Functional requirements, briefing claims to verify, metrics |

Combine them with `--profiles azure-agent,<platform>,<workload>`. Criteria are added and never
replaced. Emphasis takes the maximum across profiles. See `references/profile-authoring.md`.

**Customer profiles never live in this repository.** This repo is public. Keep customer platform
and workload profiles outside it (for example in a private repo or local folder) and pass them by
path. `.gitignore` excludes `profiles/*.yaml` as a backstop. Start from an example:

```bash
cp profiles/examples/example-platform.yaml ~/private-profiles/my-platform.yaml   # edit id, prefix, criteria
python scripts/ada.py profiles --profiles azure-agent,~/private-profiles/my-platform.yaml
```

## 5. Extend

| Change | Where | Then |
|---|---|---|
| Generic criterion | Table row in `references/domains/NN-*.md` | Run tests |
| Platform or workload criteria | `profiles/*.yaml` | `ada.py profiles --profiles …` |
| Package fields | `schemas/*.schema.json` | Update `checks.py` / `render.py` if derived; run tests |
| Sanitise rules | `scripts/ada_lib/sanitize.py` → `RULES` | Add a case to `tests/test_sanitize.py` |
| Azure collectors | `scripts/ada_lib/azure.py` (every command passes `guard`) | Add a `FakeRunner` case |
| Gates | `scripts/ada_lib/checks.py` | Add a test in `tests/` |

## 6. Review and export

1. `check` reports 0 errors. Warnings are read and either resolved or explained in
   `manifest.limitations`.
2. `package` writes `_dist/<repo>-design-assurance-<date>.zip` and `.sha256`.
3. **The development team reviews every file in the ZIP** and confirms that nothing confidential
   remains.
4. The team hands the ZIP over through its approved channel. The skill never sends, uploads or
   commits anything, and `design-assurance-output/` is git-ignored.

See `references/information-protection.md` for what is redacted, aliased or blocked.

## 7. Safety properties

| Property | Mechanism |
|---|---|
| Repository unchanged | Never executes repo code; `git status` snapshot at `init`; `repository-modified` gate |
| Prompt injection resistant | Repo content is data; `init` flags injection markers; `tests/test_prompt_injection.py` |
| Unknown ≠ 0 | `unknown-scored`, `zero-without-absence`, `unknown-without-attempts` gates |
| No secrets or internal names | Sanitise scan in `check` and again in `package`; repo, org, RG and subscription names aliased everywhere; alias map in `_work/` only |
| Azure read-only | Verb allow-list, deny-list, dry run by default, one explicit "yes" from the requester, aggregates only |

## 8. Tests

```bash
cd .github/skills/agent-design-assurance
python -m unittest discover -s tests
```

The suite covers schemas and references, unknown handling, sanitisation, prompt injection, Azure
collection (fake runner, no network), profile composition and packaging.

## 9. Layout

```text
SKILL.md                 agent entry point (progressive disclosure)
references/              methodology, scoring, Azure, protection, architecture, package, profiles
references/domains/      12 domain catalogues: method + criteria tables (source of truth)
profiles/                azure-agent.yaml only (customer profiles live outside the repo)
profiles/examples/       anonymised platform and workload examples
schemas/                 JSON Schemas for every package file and for profiles
scripts/ada.py           CLI; scripts/ada_lib/ implementation (stdlib only)
templates/               report, summary and package README templates
examples/                synthetic discovery package (regenerate: examples/build_example.py)
tests/                   unittest suite + malicious-repo fixture
```
