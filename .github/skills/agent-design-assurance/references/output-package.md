# Output package

Default location `<repo>/design-assurance-output/`, git-ignored by its own `.gitignore`.

## 1. Files

| File | Source of truth? | Content |
|---|---|---|
| `README.md` | written by you (template) | How to read the package, scope, limitations |
| `discovery-report.md` | written by you (template) | Full narrative, readable without the repo (see §2) |
| `executive-discovery-summary.md` | written by you (template) | One-page internal technical summary (see §3) |
| `manifest.json` | yes | Skill and schema versions, profiles, date, revision and tree status, modes, environments, Azure scope, sources inspected and unavailable, external doc verification, sanitisation, limitations, integrity |
| `evidence.json` | yes | All evidence records |
| `assessment.json` | yes | Criteria, observations, open questions |
| `architecture.json` | yes | Entity and relationship graph |
| `execution-flows.json` | yes | Ordered agent and workflow behaviour |
| `technology-inventory.json` | yes | Frameworks, SDKs, services, models, lifecycle (with source and verification date), native vs custom, alternatives to investigate |
| `workload-characteristics.json` | yes | Volumes, latency, limits, with `value_type` (`measured`, `configured_limit`, `business_target`, `estimate`, `briefing` or `unknown`) |
| `design-decisions.json` | yes | Decisions, rationale, alternatives, preliminary view |
| `azure-configuration.json` | yes (by `azure collect`) | Collections, aliased resources, attempts |
| `assessment.csv` | derived (`render`) | One row per criterion |
| `preliminary-observations.csv` | derived (`render`) | Observations register: ID, domain, observation, implementation, strength or gap, implication, evidence, confidence, severity, improvement, question, proposed action, owner, target date, validation status |
| `open-questions.md` | derived (`render`) | Questions by priority and audience |
| `discovery-coverage.json` | derived (`render`) | Per-domain coverage and maturity distribution; method disclosed |

**Format.** JSON files are the source of truth and are written compactly: one top-level key per
line, one array record per line. `render` normalises agent-written JSON to this form. Records link
by stable IDs (`EV-…`, criterion IDs such as `SE-03`, `OBS-…`, `Q-…`, `ENT-…`). The CSV files and `open-questions.md` are
human views of `assessment.json`; agents consuming the package should skip them.

Not packaged: `_work/` (inventory, resolved criteria, scope snapshot, alias map, allowlist),
`_dist/`, dotfiles.

## 2. Discovery report sections

Overview → scope and limitations → current implementation and maturity → known challenges →
infrastructure → logical architecture → agent architecture and execution → knowledge and data →
network and identity → `### Domain 01:` … `### Domain 12:` findings → strengths → potential gaps
and implications → decisions and rationale → workload and runtime characteristics → unknowns and
conflicts → questions. Replace every `{{…}}` placeholder (`template-placeholder` error).

## 3. Executive summary

What it does · how it is built · significant strengths · material potential gaps · important
unknowns · key dependencies · suggested focus areas for the review. It is internal and technical,
not the customer report.

## 4. Build and export

```text
ada.py render   --out P     # derived files
ada.py sanitize --out P --apply
ada.py check    --out P     # 0 errors required
ada.py package  --out P     # → P/_dist/<repo>-design-assurance-<YYYY-MM-DD>.zip + .sha256
```

`package` re-runs the gates and the sanitize scan, records the integrity block in the manifest,
and writes a **deterministic** ZIP (fixed timestamps, sorted entries) with a SHA-256 file. It never
uploads.
Partial packages are possible with `--allow-incomplete`; state this in `limitations`.

## 5. Review and handover

1. The development team unzips and reads every file. All files are text.
2. They confirm nothing confidential remains. If anything does, fix it, re-run `sanitize`,
   `check` and `package`, and confirm that the new SHA-256 differs.
3. The team hands over the ZIP and `.sha256` through its approved channel.
4. The reviewing architect checks the hash, starts with `README.md`, then
   `executive-discovery-summary.md`, then `discovery-report.md`, and uses the JSON for diagrams
   and the action register.
5. An agent consuming the package reads `manifest.json` → `discovery-coverage.json` →
   `assessment.json` (observations and questions first, then criteria filtered by status) →
   `evidence.json` by ID on demand → `architecture.json` and `execution-flows.json`.
