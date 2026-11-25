# architecture-assessment-tools

GitHub Copilot skills for assessing the design and architecture of Azure AI applications. Each
skill is a self-contained folder with a `SKILL.md` that Copilot loads when needed.

> **Use at your own risk.** Outputs support, and never replace, professional judgement. See the
> [disclaimer](#disclaimer).

## Skills

| Skill | What it does | Status |
|---|---|---|
| `agent-design-assurance` | Read-only discovery of an Azure agentic AI app (repo, plus Azure config and telemetry if allowed) across 12 domains. Produces a sanitised evidence package for independent review. | Preview |
| `foundry-estate-assessment` | Inventories an Azure AI Foundry estate and checks it against a configurable standard, with migration-effort sizing. | Preview |
| `token-quota-planner` | Sizes model capacity (TPM, RPM, concurrency) from measured usage and builds a quota request. | Experimental |
| `cost-extrapolator` | Projects production cost from a small measured sample, with confidence bands. | Experimental |
| `outcome-hypothesis` | Drafts and validates a testable outcome hypothesis with leading and lagging indicators. | Stable |
| `design-thinking` | Facilitates the 9-method Design Thinking process, from discovery to iteration. | Stable |
| `cloud-solution-architect` | Azure solution architecture guidance. From [microsoft/skills](https://github.com/microsoft/skills/tree/main/.github/skills/cloud-solution-architect). | Third-party |
| `acquire-codebase-knowledge` | Maps and documents an unfamiliar codebase. From [github/awesome-copilot](https://github.com/github/awesome-copilot/tree/main/skills/acquire-codebase-knowledge). | Third-party |

**Stable:** in regular use. **Preview:** complete and tested, not yet proven on many real
workloads. **Experimental:** early; validate every figure independently before using it for
budgets, quota requests or commitments. **Third-party:** bundled unchanged from upstream.

## Prerequisites

- GitHub Copilot CLI (`copilot`) or VS Code with GitHub Copilot.
- Git, for the copy install.
- Per-skill tools, listed in each skill's `SKILL.md` (for example, `agent-design-assurance` needs
  Python 3.10+ and, optionally, a logged-in Azure CLI).

## Install

**Copilot CLI (recommended):**

```bash
copilot plugin install jochenvw/architecture-assessment-tools
```

Update with `copilot plugin update aztools`; remove with `copilot plugin uninstall aztools`.

**VS Code, or a single skill:**

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/jochenvw/architecture-assessment-tools aztools-tmp
git -C aztools-tmp sparse-checkout set .github/skills/agent-design-assurance   # omit for all skills
```

Copy `aztools-tmp/.github/skills/<skill>` to your project's `.github/skills/` (or
`~/.copilot/skills/`), then delete `aztools-tmp`.

## Use

| Where | How |
|---|---|
| Copilot CLI (plugin) | Type `/aztools:` to list the skills, e.g. `/aztools:agent-design-assurance` |
| Copilot CLI (copied) | `/<skill>`, e.g. `/agent-design-assurance` |
| VS Code chat | Describe the task; Copilot picks the matching skill |

Example:

> /aztools:agent-design-assurance Review this repository with the azure-agent profile and produce a
> sanitised discovery package.

Customer-specific profiles for `agent-design-assurance` never belong in this repository. Keep them
elsewhere and pass them by path (`--profiles azure-agent,/path/to/platform.yaml`).

## Disclaimer

These skills and their outputs are provided "as is", without warranty of any kind, and are used
at your own risk.

- **No assurance or certification.** Outputs are AI-assisted, preliminary and may be incomplete or
  wrong. No issues found, a passing check or a favourable estimate does **not** mean a system is
  secure, compliant, well-architected, correctly sized or fit for production.
- **No rights derived.** No rights, obligations, commitments, guarantees, approvals or
  endorsements (by the authors, Microsoft or anyone else) can be derived from these skills or
  their outputs. Cost and quota figures are estimates, not quotes or capacity reservations.
- **Your responsibility.** Qualified people must review all outputs and make their own decisions.
  You remain responsible for what you run, which data you expose and what you share.
- **Not official.** A personal project; not a Microsoft product and not supported by Microsoft.

## License

[MIT](https://opensource.org/license/mit) for the skills authored here. Third-party skills keep
their upstream licenses.
