# Domain 08 — Functional assurance, correctness and human oversight

Prefix `FA` (generic) + the workload profile's prefix · Determine **which guarantees exist and where they come from**.

## Method

1. Load the workload profile. Its criteria carry the workload-specific functional requirements.
2. For every correctness claim, record the **assurance source**: application architecture, deterministic code, model instructions, evaluations, or runtime enforcement. Use `assurance_level`:
   `instructed` (prompt asks) · `evaluated` (measured against data) · `enforced` (runtime check blocks violation) · `guaranteed_by_construction` (architecture makes violation impossible).
3. Separate four properties; never merge them:
   - **Accuracy** of identified findings.
   - **Completeness** of the review (nothing relevant missed).
   - **Correctness** of supporting evidence.
   - **Faithfulness** of conclusions to that evidence.
4. A prompt that says "be exhaustive" is `instructed`, not a completeness guarantee.

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| FA-01 | Task initiation and input handling | How a task/review starts; inputs accepted; validation of inputs. | UI/API code |
| FA-02 | Content extraction fidelity | How content is extracted from inputs (text, tables, numbers, layout); known loss points. | Code |
| FA-03 | Item enumeration | Whether all items to process (claims, facts, sections) are explicitly enumerated before processing. | Code, flows |
| FA-04 | Separation of discovery, retrieval and verification | Whether these stages are distinct, testable and individually observable. | Flows, code |
| FA-05 | Verification method | Deterministic vs model-driven verification; independent validation of calculations. | Code |
| FA-06 | Challenge and multi-pass review | Independent challenge/fact-check stages; whether extra passes show measurable benefit. | Code, eval results |
| FA-07 | Missing and contradictory evidence handling | How missing, contradictory or ambiguous evidence is represented; unresolved items stay visible. | Code, output schema |
| FA-08 | Coverage and completeness evidence | How the system proves every item was processed (counts, reconciliation, coverage report). | Code, outputs |
| FA-09 | Findings persistence and output generation | Where findings are stored; report generation (Word/PDF/other); fidelity between store and report. | Code |
| FA-10 | Human review workflow | Reviewer responsibilities; preview, approve, reject, edit. | UI code, docs |
| FA-11 | Re-prompting behaviour | Whether re-prompting can silently drop earlier findings; how changes are diffed. | Code |
| FA-12 | Finding dismissal and audit | Individual dismissal; mandatory reasons; approval of incomplete reviews blocked; approval history auditable. | Code, data model |
| FA-13 | Assurance source per guarantee | For each claimed guarantee: instructed / evaluated / enforced / by construction. | Synthesis of above |

## Pitfalls

- Iterating over every document does not prove every **claim** inside it was reviewed.
- "Re-run until clean" workflows can lose findings; check whether prior findings are retained and diffed.
- Report generation can drop or reformat findings; check store-to-report reconciliation.

## Signals → targeted questions

- No explicit enumeration stage → ask how a missed item would ever be detected.
- Reviewer can approve with unresolved items and no reason → ask whether that is an accepted business rule.
- Verification and discovery done in one prompt → ask whether stage-level recall has been measured.
