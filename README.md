# copilot-skills

A small collection of standalone [GitHub Copilot](https://github.com/features/copilot)
**skills** you can drop into any project or install globally. Each skill is a self-contained
folder with a `SKILL.md` (and optional reference files) that Copilot loads on demand — no
external services, no shared setup, no dependencies between skills.

## Skills

| Skill | What it does | Use it when |
| --- | --- | --- |
| **design-thinking** | Facilitates the full Design Thinking process — a 9-method framework covering empathy-driven discovery, structured synthesis, ideation, prototyping, and production-scale iteration. | You are running user research, problem discovery, ideation, prototyping, or testing — stakeholder interviews, synthesis workshops, brainstorming, personas, journey maps, or prototype feedback. |
| **outcome-hypothesis** | Runs lightweight evidence discovery, then drafts and validates a testable **outcome hypothesis**: what business result will change, for whom, by when, and the leading/lagging indicators that prove it. | You need to turn an ambiguous goal or a "build X" request into a falsifiable, quantified, baselined outcome statement. |

Both skills are designed for general use. They ask you where to find context and where to
save output rather than assuming any fixed folder structure.

## Requirements

- [Node.js](https://nodejs.org) **18 or newer** (only needed to run the installer).
- GitHub Copilot in an editor that reads skills from `~/.copilot/skills` (global) or from a
  workspace location configured via `chat.agentSkillsLocations`.

## Install

There are two ways to install these skills: the native GitHub Copilot CLI plugin
mechanism, or the bundled `npx` installer.

### GitHub Copilot CLI plugin

This repository is a Copilot plugin (it ships a `plugin.json` manifest), so the Copilot CLI
can install it directly:

```bash
copilot plugin install jochenvw/architecture-assessment-tools
```

Manage it with `copilot plugin list`, `copilot plugin disable copilot-skills`, and
`copilot plugin uninstall copilot-skills`. You can also enable it declaratively by adding
`copilot-skills` to the `enabledPlugins` field of `~/.copilot/settings.json` (user level) or
`.github/copilot/settings.json` (repository level).

### npx installer

The installer is run directly from the repository with `npx` — it does not need to be
published to npm.

#### Global (available in every project)

Copies the skill folders into your personal Copilot skills folder (`~/.copilot/skills`):

```bash
npx github:jochenvw/architecture-assessment-tools --global
```

#### Local (just this project)

Copies the skill folders into the project (default `.copilot/skills`) and adds that path to
`.vscode/settings.json` under `chat.agentSkillsLocations`:

```bash
npx github:jochenvw/architecture-assessment-tools --local
```

Choose a different destination with `--dest`:

```bash
npx github:jochenvw/architecture-assessment-tools --local --dest .github/skills
```

Skip the settings update with `--no-settings`.

> **Global skill names share a flat namespace.** `design-thinking` and `outcome-hypothesis`
> are installed under those exact names. If you already maintain your own skills with the
> same names, prefer a **local** install (or use `--force` to overwrite knowingly). The
> installer refuses to overwrite skill folders it did not create unless you pass `--force`.

#### Options

| Flag | Effect |
| --- | --- |
| `--global` | Install into `~/.copilot/skills`. |
| `--local` | Install into the current project (default `.copilot/skills`). |
| `--dest <path>` | Destination directory for a local install. |
| `--force` | Overwrite existing skill folders without asking. |
| `--no-settings` | Skip the `.vscode/settings.json` update (local install). |
| `--clean` | Remove previous copilot-skills installs, then install. |
| `--clean-only` | Remove previous copilot-skills installs and exit. |
| `--help`, `-h` | Show usage. |

If you run the installer with no flags, it asks whether to install globally or locally.

## Uninstall

The installer records which folders it created (in a `.copilot-skills-installed.json`
marker), so cleanup only ever removes its own skills:

```bash
# Global
npx github:jochenvw/architecture-assessment-tools --clean-only

# Local (point at the folder you installed into)
npx github:jochenvw/architecture-assessment-tools --clean-only --dest .copilot/skills
```

## Manual install (no Node)

Each skill is just a folder. Copy the folders under `skills/` into your Copilot skills
location yourself:

```bash
cp -r skills/design-thinking skills/outcome-hypothesis ~/.copilot/skills/
```

## Repository layout

```text
.
├── bin/cli.mjs              # installer entry point
├── src/                     # installer implementation
├── skills/
│   ├── design-thinking/     # SKILL.md + references/methods/*
│   └── outcome-hypothesis/  # SKILL.md
├── plugin.json              # Copilot CLI plugin manifest
├── package.json
└── LICENSE
```

## License

[MIT](./LICENSE).
