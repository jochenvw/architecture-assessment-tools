# architecture-assessment-tools

Curated [GitHub Copilot](https://github.com/features/copilot) **skills** for assessing
application design & architecture. Each skill is a self-contained
`.github/skills/<name>/SKILL.md` (plus optional reference files) that Copilot loads on
demand — no shared setup and no dependencies between skills.

## Skills

| Skill | Purpose | Source |
|-------|---------|--------|
| `cloud-solution-architect` | Azure-based GenAI / Foundry-centric solution architecture guidance. | [microsoft/skills](https://github.com/microsoft/skills/tree/main/.github/skills/cloud-solution-architect) |
| `acquire-codebase-knowledge` | Systematically build and document an understanding of an unfamiliar codebase. | [github/awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/acquire-codebase-knowledge) |
| `cost-extrapolator` | Project production workload cost from a small measured PoC, benchmark, or token sample, with representativeness gating and confidence bands. | This repository |
| `token-quota-planner` | Size production model capacity (TPM / RPM / concurrency) from measured Foundry / Azure OpenAI usage or telemetry, check it against current quota limits, and produce a defensible quota request pack. | This repository |
| `design-thinking` | Facilitate the full Design Thinking process — a 9-method framework covering empathy-driven discovery, synthesis, ideation, prototyping, and production-scale iteration. | This repository |
| `outcome-hypothesis` | Run lightweight evidence discovery, then draft and validate a testable outcome hypothesis: what result will change, for whom, by when, and the indicators that prove it. | This repository |
| `poc-to-prod` | Turn a proof-of-concept GenAI application review into a polished, McKinsey-style PoC-to-production readiness report and matching PDF, steered by an engagement-notes file that sets emphasis and severity. | This repository |
| `foundry-estate-assessment` | Assess an Azure AI Foundry estate against a configurable standard using a bundled, resumable, offline-testable Python scanner (Azure CLI + stdlib only): deterministic inventory, evidence collection, PASS/FAIL/UNKNOWN rule evaluation, and migration-effort sizing. | This repository |
| `agent-design-assurance` | Read-only, evidence-first discovery of an Azure agentic AI application (repository plus optional, explicitly authorised Azure configuration) across 12 domains, using composable generic, platform and workload profiles. Produces a sanitised, portable evidence package (architecture graph, execution flows, evidence, preliminary assessment, open questions) for independent design assurance review. | This repository |

`design-thinking` and `outcome-hypothesis` are general-purpose: they ask you where to find
context and where to save output rather than assuming any fixed folder structure.

`agent-design-assurance` ships only a generic profile and anonymised examples. Customer-specific
profiles never live in this repository: keep them outside it and pass them by path
(`--profiles azure-agent,/path/to/platform.yaml`). `.gitignore` and `.npmignore` act as a backstop,
and also exclude discovery outputs (`design-assurance-output/`).

## Prerequisites

| Need | For |
|---|---|
| GitHub Copilot CLI (`copilot`) or VS Code with GitHub Copilot | Running the skills |
| Git | The VS Code / single-skill install |
| Per-skill tools | Listed in each skill's `README.md` or `SKILL.md`. For example, `agent-design-assurance` needs Python 3.10+ and, optionally, a logged-in Azure CLI (`az`) |

## Install

### Copilot CLI (recommended)

```bash
copilot plugin install jochenvw/architecture-assessment-tools
```

Installs all skills as the `aztools` plugin. Update with `copilot plugin update aztools`; remove
with `copilot plugin uninstall aztools`. If you installed it under its old name, run
`copilot plugin uninstall architecture-assessment-tools` first.

### VS Code, or a single skill

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/jochenvw/architecture-assessment-tools aztools-tmp
git -C aztools-tmp sparse-checkout set .github/skills/agent-design-assurance   # omit for all skills
```

Copy `aztools-tmp/.github/skills/<skill>` into your project's `.github/skills/` (or
`~/.copilot/skills/` for every project), then delete `aztools-tmp`. To update, repeat.

## Call a skill

| Where | How |
|---|---|
| Copilot CLI, plugin install | Type `/aztools:` to list the skills, e.g. `/aztools:agent-design-assurance` |
| Copilot CLI, copied skill | `/<skill>`, e.g. `/agent-design-assurance` |
| VS Code chat | Describe the task; Copilot loads the matching skill from `.github/skills/` |

You can also just describe the task in plain language; Copilot picks the skill from its
description. Example:

> /aztools:agent-design-assurance Run against this repository using the azure-agent profile and
> produce a sanitised discovery package.

## Repository layout

| Path | Tool | Purpose |
|------|------|---------|
| `.github/skills/` | Copilot CLI / VS Code | Skills (`<name>/SKILL.md`) |
| `.github/prompts/` | VS Code | Reusable prompts (`*.prompt.md`) |
| `.github/instructions/` | VS Code | Scoped instructions (`*.instructions.md`) |
| `.github/chatmodes/` | VS Code | Custom chat modes (`*.chatmode.md`) |
| `plugin.json` | Copilot CLI | Plugin manifest |

## License

The installer and the repository-authored skills (`cost-extrapolator`, `token-quota-planner`,
`design-thinking`, `outcome-hypothesis`, and `agent-design-assurance`) are released under the
[MIT License](https://opensource.org/license/mit). Bundled third-party skills (see **Source**
above) retain their upstream licenses.
