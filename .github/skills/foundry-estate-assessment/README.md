# foundry-estate-assessment

A self-contained Agent Skill that assesses an **Azure AI Foundry estate** against an editable
enterprise standard and sizes the effort to bring it into line.

- **Agent-facing contract:** [`SKILL.md`](SKILL.md) — when to use, operations, golden rules, result
  vocabulary, one-shot example.
- **Scanner:** `src/foundry_estate_assessment/` — a Python **stdlib-only** package that shells out to
  the **Azure CLI**. No Azure SDK, no third-party runtime dependencies.
- **Standard:** `standards/standard-foundry-v1.yaml` — the rules, parameters, effort weights and
  exceptions. Edit this, not the code.

## Quick start

```bash
cd .github/skills/foundry-estate-assessment

# 1. Preflight (read-only).
python scripts/foundry_estate_assessment.py doctor --all-accessible

# 2. Full scan of everything the current identity can read.
python scripts/foundry_estate_assessment.py scan --all-accessible --output ./out

# 3. Check progress / resume if interrupted.
python scripts/foundry_estate_assessment.py status --output ./out
python scripts/foundry_estate_assessment.py resume --output ./out

# 4. Re-score after editing the standard (no Azure calls).
python scripts/foundry_estate_assessment.py reevaluate --output ./out \
  --standard standards/standard-foundry-v1.yaml
```

Reports land in `./out/reports/`.

## Offline demo (no Azure)

```bash
python scripts/foundry_estate_assessment.py scan \
  --fixture tests/fixtures/compliant-estate --output ./demo
```

## Requirements

- Python 3.9+ (standard library only).
- Azure CLI (`az`) logged in with at least **Reader** on the target scope (see
  [`references/permissions.md`](references/permissions.md)).
- No `pip install` step. If `PyYAML` happens to be present it is used; otherwise a bundled minimal
  YAML loader parses the standard.

## Design principles

1. **Inventory first.** A stable snapshot is the denominator for all progress; detailed collection
   never starts until inventory completes.
2. **Resumable.** Every task is checkpointed to SQLite with a lease; `Ctrl+C` is always safe and
   `resume` never repeats completed work.
3. **Deterministic.** Same evidence + same standard ⇒ byte-identical CSV/JSON reports.
4. **`UNKNOWN` is never `FAIL`.** Missing evidence is surfaced for investigation, not counted as a
   defect.
5. **Secret-safe.** Credentials, tokens and Key Vault values are redacted before persistence or
   evaluation.
6. **Standard is data.** Change behaviour by editing YAML and re-evaluating, not by editing code.

## Tests

Fully offline, stdlib `unittest`, driven by the bundled fixture:

```bash
cd tests
python -m unittest discover
```

The suite covers inventory idempotency, resume/lease semantics, `UNKNOWN`-not-`FAIL`, data-driven
standard changes, shared-peripheral single-scan, Cosmos region de-duplication, secret safety,
report determinism, and reevaluate-makes-no-Azure-calls.

## Layout

```text
SKILL.md                         Agent contract
README.md                        This file
scripts/foundry_estate_assessment.py   Entry point (adds src/ to path, calls cli.main)
src/foundry_estate_assessment/   The scanner package
standards/standard-foundry-v1.yaml     The editable standard
references/                      Deep-dive docs
templates/                       Report narrative templates
tests/                           Offline tests + fixtures
```
