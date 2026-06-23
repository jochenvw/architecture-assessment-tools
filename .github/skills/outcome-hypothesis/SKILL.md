---
name: "outcome-hypothesis"
description: |
  Use when authoring an outcome hypothesis for a project, initiative, or engagement —
  a written, testable statement of what business result will change, for whom,
  within what timeframe, and validated by leading and lagging indicators with concrete
  targets. This skill runs its own evidence discovery first, then drafts and validates the
  hypothesis. Invoke when the user asks to "create an outcome hypothesis",
  "draft an outcome hypothesis", "write a hypothesis", "frame the outcome",
  "turn this into an outcome hypothesis", "what's the outcome hypothesis",
  or asks to sharpen/validate/review an existing outcome hypothesis.
---

# outcome-hypothesis

Produce a high-quality, testable **outcome hypothesis** grounded in evidence. An outcome
hypothesis is the foundation of outcome-led delivery: it converts ambiguous aspirations into
a written, falsifiable prediction that everyone can commit to, test, optimize for, and verify.

This skill is self-contained. It runs its own lightweight discovery to assess whether the
context is strong enough to author, then drafts, validates, and delivers the hypothesis.

Users may refer to this as an "outcome hypothesis", "business outcome hypothesis", "value
hypothesis", or "outcome statement" — all terms are interchangeable. Always accept any of
these terms and treat them as equivalent.

## Principles

- **Outcome, not deliverable.** The hypothesis describes a business result someone will
  experience — not a feature, MVP, or artifact. An MVP/POC is the vehicle, not the destination.
- **Falsifiable, not aspirational.** A good hypothesis can be proven wrong. "Improve customer
  experience" cannot. "Due to excessive Tier-1 handle times, we believe an AI triage assistant
  will reduce cost-to-serve, validated by AHT dropping from 8m 40s to ≤7m 20s within 90 days" can.
- **Quantify, don't assert.** Targets must be concrete numbers with units and a time horizon.
  Vague qualifiers ("significant", "material", "uplift") fail validation. If a number is
  genuinely unknown, record it as a resolution gap, not a placeholder.
- **Baseline every indicator.** Each leading and lagging indicator must have a current-state
  baseline. Without a baseline there is no "improvement" to measure. If no baseline exists,
  baselining becomes a prerequisite activity — state it explicitly.
- **Traceable.** Every hypothesis must carry an outcome chain: business outcome → lagging
  indicator → leading indicator(s) → technical intervention. If the chain cannot be drawn, the
  hypothesis is not ready.
- **Surface assumptions, don't bury them.** The load-bearing beliefs beneath the hypothesis are
  more likely to be wrong than the hypothesis itself. Record them explicitly.
- **Honest about gaps.** If context is insufficient, say so. Never fabricate a figure, baseline,
  or stakeholder name to complete the template.
- **Strict phase separation.** Do not draft the hypothesis until discovery scoring (Phase 2) is
  complete. Discovery establishes whether there is enough evidence to author responsibly.

## Context & Output

This skill makes no assumptions about where context lives or where output is saved.

- **Inputs:** Gather context from whatever sources the user has — provided documents,
  meeting transcripts, notes, issue/ticket trackers, dashboards, prior artifacts, or direct
  answers. If the user has not pointed you to any context, ask what sources to use before
  scoring discovery.
- **Outputs:** Present the full draft in chat first. Offer to save it only on request, and ask
  the user where to save it (for example a `docs/` or `output/` folder). Do not assume a fixed
  folder structure.
- **Naming convention (when saving):** `yyyy-mm-dd-<short-slug>.md` — the date drafted followed
  by a lowercase hyphenated slug. Optionally include a project or initiative name when relevant,
  e.g. `2026-04-24-my-initiative-triage-deflection.md`.
- **Sensitive material:** If working in a shared repository, remind the user not to commit
  confidential information.

## When to Use / When NOT to Use

**Use when:**

- Starting or scoping a new project and the outcome is not yet written down.
- Reviewing a proposal or brief where the outcome reads like a deliverable ("build a chatbot")
  instead of a result.
- Preparing for an outcome conversation and you need a concrete starting point.
- Converting a technical idea into an outcome-led framing.
- Validating whether an existing hypothesis is falsifiable, quantified, and baselined.

**Do NOT use for:**

- Producing a full project plan with sprints and KPIs.
- Drafting a decision record.
- General status updates or stakeholder messaging.
- Pure ideation with no evidence expectations.

---

## Authoring Flow

The skill operates in five phases. Do not skip phases. In each phase, be explicit with the
user about what is known and what is unknown.

```text
Phase 1: Gather Discovery Context  -> collect evidence from available sources (or accept user-provided context)
Phase 2: Score Readiness           -> score the D1-D7 discovery pillars and decide readiness
Phase 3: Draft Hypothesis          -> write a Full or Provisional hypothesis
Phase 4: Validate                  -> apply rules OH.1-OH.12; embed warnings, do not block
Phase 5: Deliver                   -> present the document + explicit gap list and next actions
```

---

## Phase 1 — Gather Discovery Context

Collect as much relevant evidence as possible before scoring. Prefer retrieved context over
inference.

Consult available sources in a sensible order, then synthesize:

1. User-provided materials (briefs, prior hypotheses, plans, specs, stakeholder notes).
2. Meeting transcripts and workshop outputs.
3. Any available tools and systems: issue/ticket trackers, backlog or project-management tools,
   analytics dashboards, repository context, and prior artifacts in the current workspace.
4. Direct questions to the user for unresolved gaps only.

If a source is unavailable, record the limitation and continue. If the user has provided a
ready-made discovery summary or scorecard, accept it as input and move to Phase 2 to confirm it.

Capture, at minimum:

- The business problem or opportunity, and what it costs today.
- Who is affected (the beneficiary), and how their workflow changes.
- The candidate intervention.
- Current-state measurements (baselines) and their source.
- Target outcomes, timeframe, and who owns measurement.

---

## Phase 2 — Score Readiness

Score the seven discovery pillars based on the evidence gathered in Phase 1.

| Pillar | What to evaluate |
|---|---|
| D1 Strategic context | Priority, business direction, and why now |
| D2 Problem definition | Specific pain/opportunity and business impact |
| D3 Beneficiary clarity | Who is affected and how workflows change |
| D4 Measurement baseline | Current metrics and source credibility |
| D5 Intervention clarity | Candidate capability/workflow changes in scope |
| D6 Targets and timeframe | Numeric targets and timing expectations |
| D7 Measurement ownership | Owners, cadence, and attribution approach |

Status definitions:

- **Green:** fact-based and sourced.
- **Amber:** plausible but unconfirmed.
- **Red:** missing, conflicting, or speculative.

Produce a scorecard table and **show it to the user before drafting**, so the
Full / Provisional / Investigate decision is auditable:

```markdown
| Pillar | Status | Source / Gap |
|---|---|---|
| D1 Strategic context | Green | Brief §1 + stakeholder note 2026-05-21 |
| D4 Measurement baseline | Red | No validated baseline in source systems |
```

### Readiness decision

Apply the following precedence rules in order; the first match wins:

1. **D2 is Red, or three or more pillars are Red →** *Investigate*.
2. **Any pillar is Red (and rule 1 did not match) →** *Provisional*.
3. **No Red, and at most two Amber →** *Ready to author*.
4. **Otherwise (no Red, three or more Amber) →** *Provisional*.

Decision meanings:

- **Ready to author →** draft a Full Outcome Hypothesis.
- **Provisional →** draft a Provisional Outcome Hypothesis with explicit TBD markers.
- **Investigate →** do not draft yet. Tell the user which pillars are blocking, propose
  targeted discovery actions, and loop back to Phase 1 once more evidence is available.

A current D1-D7 scorecard must exist — generated here or supplied by the user — before drafting.
If it does not, return to Phase 1 rather than drafting on weak context.

---

## Phase 3 — Draft Hypothesis

Phase 3 produces one of two document types depending on the readiness decision:

| Readiness | Document Type | Sections to produce |
|---|---|---|
| Ready to author | Full Outcome Hypothesis | The full template — title block + all five sections (see below) |
| Provisional | Provisional Outcome Hypothesis | Title block plus all five sections: complete Background, Expected Outcomes, and Open Questions & Resolution Gaps; mark Validation & Measurement and Assumptions & Risks as TBD using the placeholder below. |

For a **Provisional Hypothesis**, use the same template below but:

- Set **Status** to `Provisional` and **Confidence** to `Low` in the header.
- For each section you cannot complete, insert: `> **TBD** — This section is blocked on [specific gap from the scorecard]. Owner: [name]. Target resolution: [date].`
- The Open Questions & Resolution Gaps section is mandatory and must reflect every Red and Amber pillar.

For a **Full Hypothesis**, produce the full template below.

### The canonical hypothesis statement

Use this multi-line structure as the hypothesis headline. Render each clause as its own
paragraph separated by a blank line — do **not** wrap the statement in a blockquote (`>`):

**Due to** [business context / pain point discovered],

**We believe that** [intervention / solution approach]

**Will result in** [measurable business outcome],

**Observable by** [persona / stakeholder],

**Within** [timeframe],

**Validated by:**
- **Leading indicator 1:** [predictive metric with target]
- **Leading indicator 2:** [predictive metric with target]
- **Lagging indicator:** [outcome metric with target]

Each clause is mandatory. Leading indicators predict near-term progress and adoption; the
lagging indicator confirms the business outcome materialized. All indicators must include
concrete numeric targets with units.

A one-sentence canonical form is acceptable for a *sub-hypothesis* nested under a portfolio
hypothesis, when a single KPI carries the whole belief:

**"If we [intervention] for [beneficiary], then [KPI] will improve from [baseline] to [target] within [timeframe], as measured by [method]."**

Use the six-clause form for initiative-level, portfolio-level, or multi-outcome hypotheses.
Use the one-sentence form only for tightly-scoped pilot sub-hypotheses.

### Document template

Produce the hypothesis as a plain Markdown document. Use the section headings below **exactly
as written** in the output — do **not** prefix them with "Section N", numbering, or any other
label. Each section heading is a **level-2 Markdown heading (`##`)**; the document title is the
only level-1 heading (`#`). Render all structured content as Markdown tables — do not use HTML.

---

Begin with the document title and metadata block (this has no heading of its own):

```markdown
# Outcome Hypothesis — <<Title>>

**Date:** <<YYYY-MM-DD>>
**Author:** <<Name>>
**Project / Initiative:** <<Project — Initiative>>
**Status:** Draft | Provisional | In Review | Committed | Superseded
**Confidence:** Low | Medium | High
```

## Background

1–3 paragraphs of narrative prose that get straight to the point. Weave together, in flowing
text (not sub-headings):

- **Why this outcome matters now** — the strategic priority or vision it advances.
- **The problem and what it costs today** — the failure mode, manual work, lost revenue, or
  user pain, in operational detail.
- **Who is affected** — the beneficiary: be specific about role, segment size, geography,
  channel; describe what their workflow looks like *before* and *after*.
- **The intervention** — the specific change, described at a level an engineer could scope
  *and* a business sponsor could endorse. Avoid "build an MVP" framing — describe the
  capability or workflow change the MVP delivers.

## Expected Outcomes

The canonical hypothesis statement in the multi-line format. Render each clause as its own
paragraph separated by a blank line, with no blockquote (`>`). **Only the clause leads are
bold** — `**Due to**`, `**We believe that**`, `**Will result in**`, `**Observable by**`,
`**Within**`, `**Validated by:**`, and the `**Leading indicator N:**` / `**Lagging indicator:**`
labels. The filled-in content after each lead is normal weight.

The statement's `Validated by:` block must list at least one leading and one lagging indicator,
each with a concrete numeric target stated inline. Baselines, sources, and owners are captured
once in the indicator table under Validation & Measurement — do not repeat that operational
detail here.

If the hypothesis is a tightly-scoped pilot sub-hypothesis, the one-sentence canonical form is
permitted instead (see Phase 3 guidance).

## Validation & Measurement

**Indicator detail.** Operational detail for each indicator named in the statement. Targets and
timeframes stay in the statement; this table adds the baseline, definition, and ownership:

| Type | Indicator | Definition | Baseline | Source / Owner |
|---|---|---|---|---|
| Leading | <<Named indicator>> | <<Operational definition>> | <<Current value + measurement period>> | <<System / dashboard / owner>> |
| Lagging | <<Named indicator>> | <<Operational definition>> | <<Current value + measurement period>> | <<System / dashboard / owner>> |

At least one leading and one lagging indicator are required; one or two additional leading
indicators are allowed. More than three total dilutes focus.

**Outcome chain.** A traceable mapping: business outcome → lagging indicator → leading
indicator(s) → technical intervention. Bullet hierarchy or short Mermaid diagram.

```markdown
- **Business outcome:** <<the thing the beneficiary will experience>>
  - **Lagging indicator:** <<outcome metric that confirms it>>
    - **Leading indicator(s):** <<predictive metrics that signal progress>>
      - **Technical intervention:** <<the specific change in scope>>
      - **Technical intervention:** <<second change, if any>>
```

If the chain cannot be drawn end-to-end, **the hypothesis is not ready** — note the break point
and revisit Phase 2–3 to redraft. If the break is caused by missing evidence (no data for a
link in the chain), return to Phase 1 to gather it.

**Measurement plan.**

- How each leading and lagging indicator will be measured (system, query, cadence).
- Who runs the measurement.
- How attribution will be handled (control set, pre/post comparison, counterfactual, matched cohort).
- Checkpoint schedule for leading indicators (early — e.g. 7 / 14 / 30 days) and lagging
  indicator (e.g. 30 / 60 / 90 days post go-live). Who checks, what they look for.

## Assumptions & Risks

**Assumptions.** The load-bearing beliefs beneath the hypothesis. If any of these prove false,
the hypothesis may collapse. Present as a Markdown table:

| # | Assumption | Evidence / Status | If false, impact |
|---|---|---|---|
| A1 | <<Load-bearing belief>> | Untested / Partially supported / Evidenced | <<Which part of the hypothesis breaks>> |

Aim for 3–7 assumptions. Fewer than 3 usually means you are not looking hard enough.

**Risks & falsification criteria.**

- What conditions would falsify the hypothesis? (Be specific — a threshold on the lagging indicator.)
- What confounds could produce a false positive or false negative?
- What is the exit / pivot criteria?

## Open Questions & Resolution Gaps

Mandatory, even if empty. Each row names a specific gap, the owner, and the target resolution
date. This is where Amber and Red items from the scorecard land.

| Gap | Why it matters | Owner | Target date |
|---|---|---|---|
| <<Gap description>> | <<Why it blocks or weakens the hypothesis>> | <<Named owner or TBD>> | <<Target date>> |

---

## Phase 4 — Validate

Apply these rules in order. For each failure, embed a blockquote warning in the document
immediately after the affected section and surface it in chat:

> ⚠️ VALIDATION WARNING — Rule OH.X: <<description>>

| Rule | Section | Description |
|---|---|---|
| OH.0 | Precondition | A current D1-D7 scorecard must exist (generated in Phase 2 or provided by the user) and the readiness decision must be Ready or Provisional. If no scorecard exists, return to Phase 1; if the decision is Investigate, do not draft. |
| OH.1 | Expected Outcomes | Canonical multi-line form present, containing all of: business context ("Due to"), intervention ("We believe that"), measurable outcome ("Will result in"), persona ("Observable by"), timeframe ("Within"), and at least one leading and one lagging indicator with targets ("Validated by"). **Exception:** a tightly-scoped pilot *sub-hypothesis* may instead use the one-sentence canonical form, provided it names the intervention, beneficiary, a KPI with baseline→target, a timeframe, and the measurement method. |
| OH.2 | Expected Outcomes | Every indicator target is a **concrete number with units** (e.g. "≥85%", "≤7m 20s", "$5M"). Vague qualifiers ("significant", "material", "uplift") fail. |
| OH.3 | Expected Outcomes | Timeframe is a **specific window** anchored to an event or date ("within 90 days of go-live", "by end of FY26 H1"). "Soon", "over time", "medium term" fail. |
| OH.4 | Expected Outcomes | Persona is a **specific role, segment, or business unit** — not "users" or "the customer". |
| OH.5 | Background | Intervention describes a **capability or workflow change** — not an artifact ("MVP", "POC", "chatbot"). An MVP is acceptable only as a delivery vehicle *alongside* the capability description. |
| OH.6 | Validation & Measurement | Lagging indicator has a named source system or dashboard and a named owner (or an explicit "Owner TBD — resolution by <<date>>" note). |
| OH.7 | Validation & Measurement | Each indicator baseline is a numeric current-state value *or* is explicitly marked "No baseline exists — baselining is a prerequisite activity", with a target completion date. Missing baseline without this acknowledgement fails. |
| OH.8 | Validation & Measurement | Chain is complete end-to-end: business outcome → lagging indicator → leading indicator(s) → intervention. Breaks in the chain fail. |
| OH.9 | Validation & Measurement | Measurement plan names *who* measures, *how*, and *at what cadence/checkpoints* for both leading and lagging indicators. |
| OH.10 | Assumptions & Risks | At least three assumptions listed. Each has a status (Untested / Partially supported / Evidenced) and an "if false" impact. |
| OH.11 | Assumptions & Risks | At least one explicit condition under which the hypothesis would be considered disproved. |
| OH.12 | Open Questions & Resolution Gaps | Every Amber or Red item from the scorecard is reflected in the Open Questions & Resolution Gaps table. |

If **any of OH.1, OH.2, OH.3, OH.7, or OH.8** fail, the hypothesis is **not investable** — say
so explicitly to the user and recommend returning to Phase 1 to strengthen the weak pillars.

---

## Phase 5 — Deliver

1. Present the complete document to the user inline.
2. Summarize: readiness outcome (Ready to author / Provisional / Investigate), whether it
   passed validation (investable or not), confidence level, top 3 gaps, and recommended next actions.
3. Offer to write the document to disk (ask the user for the location, per Context & Output).
4. If the user wants a `.docx` or `.pdf` deliverable, convert the Markdown with their preferred
   tool. Do not generate binary files from this skill directly.

---

## Guardrails

- **Never fabricate baselines, targets, or owners.** If unknown, mark as a gap.
- **Do not bypass the readiness scorecard.** Producing a polished-looking hypothesis on weak
  context is the primary failure mode this skill exists to prevent.
- **Present the draft before writing to disk.** Always show the user the full document first;
  write only on confirmation.
- **Respect confidentiality.** If source material is protected and cannot be read, say so — do
  not infer its contents.
- **Stay outcome-led.** If the user pushes to frame the hypothesis as "deliver an MVP", redirect
  to "the MVP will cause *which measurable change*?"

---

## Common Failure Modes (and Fixes)

| Failure mode | Fix |
|---|---|
| Hypothesis reads like a project brief ("We will build X") | Rewrite in "Due to … We believe that … Will result in …" form with leading and lagging indicators. |
| Target is "measurable uplift" or "~ 10-20%" | Force a single committed number; if unknown, mark as a gap with owner + date. |
| No baseline | Either retrieve one, or declare baselining as the first activity. Do not proceed with "uplift vs. baseline" if none exists. |
| Beneficiary is "users" | Ask: which role, which segment, how many? Replace with the specific answer. |
| Only one assumption listed | Push harder — assumptions about data quality, adoption, attribution, and commercial model are almost always load-bearing. |
| No falsification condition | Add one: "The hypothesis is disproved if the lagging indicator moves less than X within the timeframe." |
