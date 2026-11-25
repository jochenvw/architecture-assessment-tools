---
name: foundry-estate-assessment
description: >-
  Use this skill to assess an Azure AI Foundry estate: discover every accessible Foundry (and classic
  hub) account, profile its projects, model deployments, bring-your-own-data connections, networking,
  gateway (APIM) and observability, evaluate them against an editable enterprise standard, and produce
  deterministic compliance and migration-effort reports. Use when the user wants a Foundry estate
  inventory, a pattern/standard conformance review, a migration or upgrade sizing, or a resumable
  large-scale scan of many subscriptions. Do NOT use for pure token/quota planning, cost extrapolation,
  or building a new Foundry from scratch.
---

# Foundry Estate Assessment

Assess an **Azure AI Foundry estate** against an enterprise pattern and size the effort to bring it
into line. The skill has two clearly separated parts:

```text
Agent Skill (this SKILL.md + references/)  →  explains, decides scope, invokes the scanner, interprets results
Bundled scanner (src/ + scripts/)          →  deterministic inventory, checkpointing, rule evaluation, reports
Editable ruleset (standards/*.yaml)         →  the standard itself — change it WITHOUT touching code
```

The scanner is a **stdlib-only Python package** that shells out to the **Azure CLI**. It has **no
external runtime dependencies** and no Azure SDK. Everything it learns is persisted to a local SQLite
database so a scan is **resumable** and reports can be regenerated offline.

## WHEN TO USE

- Inventory of all Foundry / AI Services / classic-hub accounts across accessible subscriptions.
- Conformance of an estate to an enterprise Foundry pattern (networking, BYO-data auth, gateway, etc.).
- Migration / upgrade **effort sizing** (classic hub → current, private-networking rollout, data moves).
- Large, long-running scans that must survive interruption and resume where they left off.

## DO NOT USE FOR

- Token / TPM / quota planning (use `token-quota-planner`).
- Cost estimation or unit economics (use `cost-extrapolator`).
- Greenfield Foundry design or deployment.
- Certifying an estate as "secure" or "compliant" — this produces evidence-based observations, not
  a sign-off.

## Golden rules (read before running)

1. **Never convert `UNKNOWN` to `FAIL`.** Missing or uncollectable evidence is `UNKNOWN`, never a
   failure. A rule fails only when evidence positively contradicts the standard.
2. **Do not inspect every resource by hand.** Let the scanner enumerate and profile resources. Your
   job is scope, invocation and interpretation — not clicking through the portal.
3. **`--all-accessible` is not tenant-wide.** It means "every subscription this identity can read".
   Say so in the report; unreadable subscriptions are listed as gaps, not passes.
4. **Secrets are never collected.** Keys, tokens, connection strings and Key Vault secret values are
   redacted before anything is written or evaluated. Do not try to work around this.
5. **Reports are deterministic.** The scanner produces the CSV/JSON/Markdown; you add narrative on
   top. Do not fabricate numbers the scanner did not emit.

## Result vocabulary

| Result | Meaning | Your interpretation |
| --- | --- | --- |
| `PASS` | Evidence demonstrates adherence to the standard. | Adherent. |
| `FAIL` | Evidence positively contradicts the standard. | Improvement recommendation. |
| `UNKNOWN` | Required evidence was missing, blocked, or insufficient. | Investigate; do **not** treat as failure. |
| `NOT_APPLICABLE` | Rule does not target this resource classification. | Ignore for this resource. |
| `ERROR` | The rule itself could not be evaluated (mis-authored). | Fix the rule. |
| `ACCEPTED_EXCEPTION` | An underlying `FAIL` is covered by an unexpired, documented exception. | Note as an accepted, time-boxed deviation. |

When you write findings, frame `FAIL` results as **constructive improvement recommendations**, not
accusatory defect labels.

## Operations

Run everything through the bundled entry point:

```bash
python scripts/foundry_estate_assessment.py <command> [options]
```

| Command | Purpose |
| --- | --- |
| `doctor` | Preflight: identity, Azure CLI, accessible subscriptions. Makes read-only calls. |
| `inventory` | Build a stable inventory snapshot only (the denominator for progress). |
| `scan` | Inventory, then collect evidence, evaluate rules, and write reports. |
| `resume` | Continue an interrupted scan against the **same** snapshot (no re-inventory). |
| `refresh` | Take a **new** snapshot and rescan (picks up newly created resources). |
| `status` | Show progress: subscriptions, Foundries, per-collector task counts. |
| `report` | Regenerate reports from already-collected evidence. |
| `reevaluate` | Re-run the standard against stored evidence. **Makes no Azure calls.** |

Common options: `--output <dir>` (state + reports, required for most commands), `--standard <yaml>`
(defaults to `standards/standard-foundry-v1.yaml`), `--concurrency <n>`, `--no-raw-evidence`,
`--retry-blocked`, and a scope selector (`--all-accessible`, `--subscription`, `--resource-id`,
`--resource-group`, `--management-group`).

## Keep the caller informed

The caller should never wonder what you are doing or why. Post a short update (1-3 lines, plain
language) at each step:

- **Before:** what you are about to do and why it matters for the result.
- **After:** what you found, including gaps or surprises, and what happens next.
- **On a pivot or blocker:** say so immediately, with the reason and the impact on the result.

Make assumptions visible as you make them. Do not narrate every command; report progress.

## Recommended flow

```text
1. doctor      → confirm login + scope before spending time.
2. scan        → full pass; Ctrl+C is safe at any time.
3. status      → see what remains (blocked / retryable / pending).
4. resume      → finish anything interrupted or transiently blocked (--retry-blocked for permissions).
5. report      → hand the reports/ directory to the narrative step.
6. reevaluate  → after editing the standard YAML, re-score with zero Azure calls.
```

## One-shot worked example (offline fixture)

The skill ships a self-contained fixture so you can see the whole pipeline without Azure:

```bash
cd .github/skills/foundry-estate-assessment
python scripts/foundry_estate_assessment.py scan \
  --fixture tests/fixtures/compliant-estate \
  --output /tmp/fea-demo
```

This discovers two Foundries (`team-a-foundry`, a current account; `team-b-foundry`, a classic hub),
profiles a shared Azure AI Search service **once**, records the APIM gateway relationship, and writes
`reports/executive-summary.md` plus stable CSV/JSON. Then edit `standards/standard-foundry-v1.yaml`
and run:

```bash
python scripts/foundry_estate_assessment.py reevaluate --output /tmp/fea-demo \
  --standard standards/standard-foundry-v1.yaml
```

to re-score the collected evidence — with **no** Azure calls.

## Reports the scanner writes

Under `<output>/reports/`:

- `executive-summary.md` — human-readable summary (scope caveats, adherence, unknowns, effort).
- `foundries.csv`, `projects.csv`, `model-footprint.csv` — the inventory and model surface.
- `findings.csv` — every rule result with expected/actual/explanation/recommended investigation.
- `unknowns.csv` — the investigation backlog (what could not be proven and why).
- `relationships.csv` — proven/inferred edges (project→data service, foundry→gateway, etc.).
- `peripheral-footprint.csv` — shared data services with fan-in (how many Foundries reference each).
- `migration-effort.csv` — deterministic S/M/L/XL bands with the drivers behind each.

## Interpreting effort

Effort bands are derived from **drivers** (architecture generation, project/deployment counts, data
footprint, shared dependencies, networking/identity complexity, unknown evidence) — **never** from the
count of failed rules. Compliance status, migration effort, data footprint and confidence are reported
independently. A Foundry can be fully adherent yet still `XL` to migrate because of its data footprint.

## References

- `references/architecture.md` — how the scanner is structured and why.
- `references/permissions.md` — least-privilege access the scan needs.
- `references/evidence-model.md` — evidence, provenance, sanitization, SQLite schema.
- `references/rule-authoring.md` — how to edit or extend the standard YAML.
- `references/migration-sizing.md` — the effort model and its drivers.
- `references/worked-example.md` — a full annotated fixture run.
- `templates/executive-report.md`, `templates/foundry-detail.md` — narrative report skeletons to
  fill from the deterministic CSV/JSON/Markdown outputs.

## Editing the standard

The standard is the single source of truth and is **meant to be edited**. Change parameters (expected
SKU, accepted gateway generation, central platform resource IDs), add or remove rules, or add
time-boxed exceptions — then `reevaluate`. You never need to change scanner code to change the standard.
