# Profile authoring and composition

A discovery uses **one generic profile plus zero or more platform and workload profiles**.
Profiles are YAML, validated against `schemas/profile.schema.json`, and editable without touching
code.

## 1. Kinds

| Kind | Purpose | Shipped |
|---|---|---|
| `generic` | Selects domain catalogues (`include_domains`) and sets base emphasis | `azure-agent.yaml` |
| `platform` | Customer platform standard: networking, identity, landing zone, tooling | `examples/example-platform.yaml` (fictional) |
| `workload` | Functional requirements for one application, plus briefing claims to verify | `examples/example-document-review.yaml` (fictional) |

Customer profiles **never live in this repository**. Keep them outside it and pass them by path.
`.gitignore` excludes `profiles/*.yaml` (except `azure-agent.yaml`) as a backstop.

## 2. Selecting and combining

```text
ada.py profiles                                         # list available
ada.py profiles --profiles azure-agent,../private/my-platform.yaml,../private/my-workload.yaml  # show the resolved set
ada.py init ... --profiles azure-agent,../private/my-platform.yaml,../private/my-workload.yaml
```

`--profiles` accepts IDs (looked up in `profiles/` and `profiles/examples/`) or paths to `.yaml`
files. Use paths for customer profiles.

Resolution rules:

1. At least one `generic` profile; no duplicates; each `requires` entry must be selected.
2. Generic criteria come from the selected domain catalogues. Profile criteria are **added**.
   They never replace catalogue criteria; an ID collision is an error.
3. Emphasis is the **maximum** across profiles (`standard` < `high` < `critical`). It is applied
   per domain (`target: '08'`) or per criterion (`target: GRD-04`).
4. `related` IDs must exist in the resolved set. Briefing `verify_with` IDs must exist too.
5. The resolved set is frozen in `_work/resolved-criteria.json` and `manifest.profiles`. `check`
   flags `criterion-missing`, `criterion-unexpected` or `profile-mismatch` if they drift. Re-run `init --force` to change them.

## 3. Schema

```yaml
profile:
  id: my-platform                 # file name without .yaml
  kind: platform                  # generic | platform | workload
  version: 0.1.0
  title: …
  description: …
  baseline_status: briefing_unverified   # generic_guidance | briefing_unverified | verified_policy
  provenance: Where the standard came from
  criterion_prefix: MYP           # all criteria IDs must start with MYP-
  requires: [azure-agent]
emphasis:
  - {target: '04', level: high, reason: …}
criteria:
  - id: MYP-01
    domain: '04'                  # one of the twelve
    title: …
    question: …                   # what to investigate
    expected_baseline: …          # what good looks like
    baseline_source: Standard X v2 §3   # cite it
    related: [CS-03, SG-06]       # generic criteria this refines
    evidence_hints: [IaC modules, az network private-endpoint list]
    follow_up_questions: [ … ]
    emphasis: critical
briefing:                         # workload profiles
  summary: …
  claims:
    - {id: BR-01, statement: "Every claim is verified against source", verify_with: [MYW-01, FA-03]}
  focus_areas: [ … ]
workload_metrics:
  - {name: documents per month, why: sizing, criteria: [OS-05]}
```

## 4. Baseline status

| Value | Meaning | Effect |
|---|---|---|
| `generic_guidance` | General practice and the Well-Architected Framework | Gaps are "differs from common practice" |
| `briefing_unverified` | From a briefing; not checked against a published standard | Present as context to verify; never as policy |
| `verified_policy` | Confirmed published customer policy | Gaps may be described as deviations from policy |

## 5. Extending the generic catalogue

The domain catalogues are the criteria tables in `references/domains/NN-*.md`, which
`ada_lib.catalogue` parses. To add a generic criterion, add a table row with the next ID for that
domain's prefix. Then run `python -m unittest discover -s tests`; the reference tests check that
IDs are unique and parse correctly.
