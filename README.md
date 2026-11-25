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
(`--profiles azure-agent,/path/to/platform.yaml`). `.gitignore` and `.npmignore` act as a backstop, as are discovery outputs (`design-assurance-output/`).

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

To use these skills in another project or globally, pick the first option that fits:

| You use | Recommended | Needs |
|---|---|---|
| GitHub Copilot CLI | [Plugin](#github-copilot-cli-plugin) | Copilot CLI only |
| VS Code, or only one skill | [Copy with git](#copy-with-git-no-npm) | Git only |
| Either, and npm is allowed to fetch from GitHub | [npx installer](#npx-installer) | Node.js 18+ |

### GitHub Copilot CLI plugin

This repository ships a `plugin.json` manifest, so the Copilot CLI can install it directly:

```bash
copilot plugin install jochenvw/architecture-assessment-tools
```

The plugin is named `aztools`, so its skills are grouped under one
prefix when you type `/`: `/aztools:agent-design-assurance`, `/aztools:cost-extrapolator`,
`/aztools:token-quota-planner`, and so on.

Manage it with `copilot plugin list`, `copilot plugin update aztools` (pulls the latest from
`main`), `copilot plugin disable aztools` and `copilot plugin uninstall aztools`. You can also
enable it declaratively by adding `aztools` to the `enabledPlugins` field of
`~/.copilot/settings.json` (user level) or `.github/copilot/settings.json` (repository level).

If you installed it before the plugin was renamed to `aztools`, uninstall the old
`architecture-assessment-tools` plugin and install it again.

### Copy with git (no npm)

Works anywhere Git works. Fetch one skill (or drop the `sparse-checkout` line for all of them):

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/jochenvw/architecture-assessment-tools aztools-tmp
git -C aztools-tmp sparse-checkout set .github/skills/agent-design-assurance
```

Copy `aztools-tmp/.github/skills/<skill>` into your project's `.github/skills/` (or
`~/.copilot/skills/` for every project), then delete `aztools-tmp`. To update, repeat.

### npx installer

The installer runs directly from the repository with `npx` — it does not need to be published
to npm.

> **npm 12 and locked-down npm.** npm 12 refuses git-hosted packages by default
> (`EALLOWGIT`), and some corporate npm mirrors trigger `EALLOWREMOTE`. Allow them for this one
> command only, without changing your npm configuration:
>
> ```bash
> npx --allow-git=all --allow-remote=all github:jochenvw/architecture-assessment-tools --local
> ```
>
> If your organisation's policy forbids that, use the [plugin](#github-copilot-cli-plugin) or
> [copy with git](#copy-with-git-no-npm) instead.

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
`design-thinking`, `outcome-hypothesis`, and `agent-design-assurance`) are released under the
[MIT License](https://opensource.org/license/mit). Bundled third-party skills (see **Source**
above) retain their upstream licenses.
