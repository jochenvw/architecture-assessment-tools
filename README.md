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

`design-thinking` and `outcome-hypothesis` are general-purpose: they ask you where to find
context and where to save output rather than assuming any fixed folder structure.

## Prereqs

- VS Code with GitHub Copilot, or the GitHub Copilot CLI (`copilot`).
- [Node.js](https://nodejs.org) **18 or newer** — only needed to run the installer.
- Some skills need extra tooling. For example, `cloud-solution-architect` expects an Azure
  subscription with Azure AI Foundry access and the Azure CLI (`az`) authenticated
  (`az login`).

## Use the skills in this repository

- CLI: skills are auto-discovered from `.github/skills/`.
- VS Code: customizations under `.github/` are auto-loaded.

## Install the skills elsewhere

To use these skills in another project or globally, install them with the native Copilot CLI
plugin mechanism or with the bundled `npx` installer.

### GitHub Copilot CLI plugin

This repository ships a `plugin.json` manifest, so the Copilot CLI can install it directly:

```bash
copilot plugin install jochenvw/architecture-assessment-tools
```

Manage it with `copilot plugin list`, `copilot plugin disable architecture-assessment-tools`,
and `copilot plugin uninstall architecture-assessment-tools`. You can also enable it
declaratively by adding `architecture-assessment-tools` to the `enabledPlugins` field of
`~/.copilot/settings.json` (user level) or `.github/copilot/settings.json` (repository level).

### npx installer

The installer runs directly from the repository with `npx` — it does not need to be published
to npm.

#### Global (available in every project)

Copies the skill folders into your personal Copilot skills folder (`~/.copilot/skills`) — the
location Copilot discovers automatically in every project, no settings change required:

```bash
npx github:jochenvw/architecture-assessment-tools --global
```

#### Local (just this project)

Copies the skill folders into the project's `.github/skills` folder, which both the Copilot
CLI and VS Code discover automatically — no settings change required:

```bash
npx github:jochenvw/architecture-assessment-tools --local
```

Choose a different destination with `--dest`. For any location other than `.github/skills`,
the installer registers that path in `.vscode/settings.json` under `chat.agentSkillsLocations`
(skip this with `--no-settings`):

```bash
npx github:jochenvw/architecture-assessment-tools --local --dest .copilot/skills
```

> **Global skill names share a flat namespace.** If you already maintain your own skills with
> the same names, prefer a **local** install (or use `--force` to overwrite knowingly). The
> installer refuses to overwrite skill folders it did not create unless you pass `--force`.

#### Options

| Flag | Effect |
| --- | --- |
| `--global` | Install into `~/.copilot/skills`. |
| `--local` | Install into the current project (default `.github/skills`). |
| `--dest <path>` | Destination directory for a local install. |
| `--force` | Overwrite existing skill folders without asking. |
| `--no-settings` | Skip the `.vscode/settings.json` update (used only for non-default destinations). |
| `--clean` | Remove previous installs from this package, then install. |
| `--clean-only` | Remove previous installs from this package and exit. |
| `--help`, `-h` | Show usage. |

If you run the installer with no flags, it asks whether to install globally or locally.

### Uninstall

The installer records which folders it created (in an `.installed-skills.json` marker), so
cleanup only ever removes its own skills:

```bash
# Global
npx github:jochenvw/architecture-assessment-tools --clean-only

# Local (point at the folder you installed into)
npx github:jochenvw/architecture-assessment-tools --clean-only --dest .github/skills
```

## Repository layout

| Path | Tool | Purpose |
|------|------|---------|
| `.github/skills/` | Copilot CLI / VS Code | Skills (`<name>/SKILL.md`) |
| `.github/prompts/` | VS Code | Reusable prompts (`*.prompt.md`) |
| `.github/instructions/` | VS Code | Scoped instructions (`*.instructions.md`) |
| `.github/chatmodes/` | VS Code | Custom chat modes (`*.chatmode.md`) |
| `bin/`, `src/` | Node | `npx` installer |
| `plugin.json` | Copilot CLI | Plugin manifest |

## License

The installer and the repository-authored skills (`cost-extrapolator`, `token-quota-planner`,
`design-thinking`, and `outcome-hypothesis`) are released under the
[MIT License](https://opensource.org/license/mit). Bundled third-party skills (see **Source**
above) retain their upstream licenses.
