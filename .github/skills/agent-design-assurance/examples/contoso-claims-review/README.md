# Design assurance discovery package: Contoso claims reviewer (synthetic)

Read-only, evidence-first discovery output produced by the
`agent-design-assurance` skill. Sanitised for manual handover. Review with the
development team before sharing.

## Read in this order

Humans:

1. `executive-discovery-summary.md`: one-page technical summary.
2. `discovery-report.md`: full narrative, all twelve domains.
3. `open-questions.md`: prioritised questions for the team.
4. `preliminary-observations.csv`: strengths and potential gaps.
5. `assessment.csv`: per-criterion maturity, confidence, coverage.

AI agents (the JSON files are the source of truth; skip the rest):

1. `manifest.json`: scope, what was and was not inspected, limitations.
2. `discovery-coverage.json`: totals and per-domain counts. Use it to decide what to load next.
3. `assessment.json`: `observations` and `open_questions` first, then `criteria`. Filter
   criteria on `status != "unknown"` for findings and `status == "unknown"` for gaps.
4. `evidence.json`: resolve `EV-…` IDs on demand; do not load it all up front.
5. `architecture.json`, `execution-flows.json`, then the remaining JSON files as needed.

Skip `assessment.csv`, `preliminary-observations.csv` and `open-questions.md`: they are
generated views of `assessment.json`. JSON files hold one record per line, so `grep "BC-01"`
returns a single complete record. IDs: criteria `<PREFIX>-nn`, evidence `EV-…`, observations
`OBS-nnn`, questions `Q-nnn`, entities `ENT-…`, aliases `AZ-…`, `APP-n`, `ORG-n`.

## Machine-readable files

| File | Content |
| --- | --- |
| `manifest.json` | Scope, profiles, modes, revision, sanitisation, limitations |
| `evidence.json` | Evidence register; every claim resolves to an `EV-…` ID |
| `assessment.json` | Criteria, observations, open questions |
| `architecture.json` | Entities, relationships, diagram views |
| `execution-flows.json` | Ordered agent/application flows |
| `technology-inventory.json` | Languages, SDKs, services, versions |
| `workload-characteristics.json` | Declared and measured workload values |
| `design-decisions.json` | Documented and inferred decisions |
| `azure-configuration.json` | Deployed configuration (aliased), if collected |
| `discovery-coverage.json` | Coverage per domain (rendered) |

## Reading the scores

- Maturity `0`-`5`: evidence-backed. `0` means confirmed absence.
- `U`: unknown, not zero. Discovery attempts are recorded.
- `N/A`: not applicable, with justification.
- Perspectives: declared (docs) → implemented (code) → deployed (Azure) →
  runtime (telemetry). Each evidence item states its perspective.

## Information protection

Identifiers are aliased consistently: Azure resources, resource groups and subscriptions
(`AZ-…`), the repository, organisation and other internal names (`APP-n`, `ORG-n`, `TEAM-n`,
`SYSTEM-n`, `TERM-n`), `IP-n` and `person-n@example.invalid`. The alias map stays with the
team that produced the package. Secrets, raw documents, prompts, logs and financial figures are
excluded. See `manifest.json` → `sanitisation` for counts and exclusions.

## Scope note

Repository and test-environment Azure configuration inspected; production, telemetry and role assignments not inspected.
