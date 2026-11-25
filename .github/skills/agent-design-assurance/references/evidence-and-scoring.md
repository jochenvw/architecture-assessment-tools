# Evidence and scoring

Evidence is the primary deliverable. Scores support the reviewer; they are not the verdict.

## 1. Evidence record (`evidence.json`)

| Field | Rule |
|---|---|
| `id` | Stable, unique, e.g. `EV-AE-003`, `AZ-FOUNDRY-1` |
| `criteria` | Criterion IDs this evidence informs |
| `source_type` | e.g. `source_code`, `iac`, `prompt`, `azure_resource_config`, `telemetry_aggregate`, `interview` |
| `classification` | `observed`, `documented`, `inferred`, `conflicting`, `unknown` or `not_applicable` |
| `perspective` | `declared`, `implemented`, `deployed`, `runtime`, `briefing` or `none` |
| `location` | `{path, lines, symbol, config_path}`, repo-relative; never absolute |
| `repository_revision` | commit SHA (set by `init`) |
| `azure_resource` | `{alias, type, location}`; alias only, never real names |
| `description` | **Semantic**, self-contained, sanitised. What exists, how it behaves, why it matters. No verbatim code or prompt text. |
| `command_template` | Command or query with placeholders, for Azure-derived items |
| `confirms_absence` | `true` when the item documents a search that found nothing |
| `limitations` | What this evidence cannot show |

Confirmed absence is evidence too. Example: "Searched all Python modules and pipeline definitions
for evaluation runners; none exist." (`confirms_absence: true`). That record supports maturity `0`;
silence does not.

## 2. Criterion assessment (`assessment.json` → `criteria[]`)

The skeleton is created by `init`, with one entry per resolved criterion. Fill in:

| Field | Meaning |
|---|---|
| `applicability` + `applicability_justification` | `not_applicable` needs a justification, status `not_applicable` and maturity `N/A` |
| `status` | What the evidence shows (same vocabulary as classification) |
| `current_implementation`, `technical_details`, `design_rationale` | Description of what exists |
| `strengths`, `potential_gaps`, `implications`, `constraints`, `dependencies` | Constructive analysis |
| `perspectives` | Which perspectives (declared, implemented, deployed, runtime) the evidence covers |
| `conflicting_evidence`, `unknowns`, `discovery_attempts` | What is unresolved and how you looked |
| `assurance_level` | `instructed` (prompt says so), `evaluated` (measured), `enforced` (code or policy), `guaranteed_by_construction`, … |
| `maturity` | `0`–`5`, `U` or `N/A` |
| `confidence` | `high`, `medium`, `low` or `none` |
| `discovery_coverage` | `complete`, `partial`, `attempted` or `not_investigated` |
| `risk_severity` | Preliminary risk (`high`, `medium`, `low`, `informational` or `not_assessed`); independent of maturity |
| `evidence_refs`, `validation_evidence_refs` | Supporting evidence; validation evidence (tests, evaluation results, telemetry) |
| `absence_confirmed` | `true` only with evidence where `confirms_absence` is true |
| `follow_up_questions`, `improvement_opportunities` | Next steps |

## 3. Maturity scale

| Score | Meaning | Minimum evidence |
|---|---|---|
| 0 | Confirmed absent | Status `observed`, `absence_confirmed`, evidence with `confirms_absence` |
| 1 | Initial or ad hoc | ≥1 evidence ref |
| 2 | Partially implemented | ≥1 evidence ref |
| 3 | Adequately implemented | ≥1 evidence ref |
| 4 | Well implemented | ≥1 evidence ref |
| 5 | Mature, with validation evidence | `validation_evidence_refs` |
| U | Unknown | Discovery attempts recorded |
| N/A | Not applicable | Justification |

Independence rules:

- maturity ≠ severity ≠ compliance;
- `instructed` (a prompt asks for it) is **not** `enforced`, and is rarely above 2;
- confidence describes the evidence, not the implementation.

## 4. Quality gates (`ada.py check`)

| Gate | Error code(s) |
|---|---|
| Schema-valid JSON | `schema` |
| All IDs resolve (evidence, criteria, entities, flow steps) | `unresolved-*` |
| Criteria match resolved profiles | `criterion-missing`, `criterion-unexpected`, `profile-mismatch` |
| Every criterion and domain investigated | `not-investigated`, `domain-skipped` |
| Unknown handled honestly | `unknown-scored`, `unknown-without-attempts` |
| Scores supported | `score-without-evidence`, `score-without-confidence`, `zero-without-absence`, `five-without-validation`, `absence-unsupported` |
| Conflicts and N/A explained | `conflict-undescribed`, `na-inconsistent`, `na-unjustified` |
| Status and coverage consistent | `status-without-evidence`, `coverage-without-attempts` |
| Azure scope authorised | `azure-mode-undeclared`, `azure-unauthorised`, `telemetry-unauthorised` |
| Rendered files complete and current | `template-placeholder`, `render-stale` |
| Nothing sensitive | `sensitive-secret`, `sensitive-identifier`, `sensitive-manual_review` |
| Repository untouched | `repository-modified` |
| Questions anchored | `question-unanchored` |

Warnings cover issues such as roadmap language, missing report domain sections, orphaned evidence,
missing strengths, non-constructive gaps, and high-emphasis unknowns without a question. Resolve
them or explain them in `limitations`.

## 5. Aggregation

`render` writes `discovery-coverage.json` per domain: counts per maturity level, U, N/A, coverage
and `mean_of_scored` (numeric only; U and N/A excluded). The method is disclosed in
`scoring_method`. **No overall application score.** Always quote the denominator when citing a
domain mean.

## 6. Observations (`assessment.json` → `observations[]`)

| Category | Use for |
|---|---|
| `retain` | Sound implementation or decision worth keeping |
| `improve` | Exists, could be refined |
| `introduce` | Appears missing |
| `reconsider` | Decision worth comparing with alternatives |
| `investigate` | Needs more evidence |

Each observation states what is implemented, why it matters, its evidence, and what needs
clarification (`existing_implementation`, `implication`, `evidence_refs`,
`needs_clarification`, `improvement_options`). Leave `owner` and `target_date` empty and set `validation_status` to
`unvalidated` unless the team agreed otherwise. Do not prescribe changes without context; list
options and trade-offs.

## 7. Questions (`assessment.json` → `open_questions[]`)

Evidence-driven and anchored to criteria or evidence (`P1` changes recommendations, `P3` is
detail). Example: "The prompt is loaded from Cosmos DB at runtime (EV-AE-011). How are prompt
versions approved and regression-tested?" Avoid questions that only restate a criterion.
