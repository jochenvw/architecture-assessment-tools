# architecture-assessment-tools

Curated skills for assessing Azure-based GenAI application design & architecture (Foundry-centric).

## Prereqs
- Azure subscription + access to Azure AI Foundry
- Azure CLI (`az`) authenticated (`az login`)
- VS Code w/ GitHub Copilot, or GitHub Copilot CLI (`copilot`)

## Layout
| Path | Tool | Purpose |
|------|------|---------|
| `.github/skills/` | Copilot CLI | Skills (`<name>/SKILL.md`) |
| `.github/prompts/` | VS Code | Reusable prompts (`*.prompt.md`) |
| `.github/instructions/` | VS Code | Scoped instructions (`*.instructions.md`) |
| `.github/chatmodes/` | VS Code | Custom chat modes (`*.chatmode.md`) |

## Use
- CLI: skills auto-discovered from `.github/skills/`.
- VS Code: customizations auto-loaded from `.github/`.
