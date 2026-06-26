---
name: "design-thinking"
description: "Use when facilitating or coaching teams through user research, problem discovery, ideation, prototyping, or testing — covers all 9 Design Thinking methods from scope conversations to production iteration. Invoke for stakeholder interviews, synthesis workshops, brainstorming sessions, persona development, journey mapping, or prototype feedback."
---

# design-thinking

Facilitate the Design Thinking process — a 9-method framework covering empathy-driven discovery, structured synthesis, creative ideation, rapid prototyping, and production-scale iteration.

## Context & Output

This skill is standalone and makes no assumptions about where you store work.

- **Inputs:** If the user has existing context (research notes, transcripts, prior artifacts), ask them to point you to it. Do not assume a fixed folder structure.
- **Outputs:** When the user asks to save an artifact, ask where to save it (for example a `docs/` folder, an `output/` folder, or any path they prefer) before writing. Present generated content in chat first; write to disk only on confirmation.
- **Sensitive material:** If working in a shared repository, remind the user not to commit confidential information.

## Principles

- Concise (2–4 sentences), empathetic, human; no emojis unless requested.
- Think in patterns, speak in observations, and empower the user with choices rather than directives.
- End guidance with 2–3 next-step options + a quick self-assessment (e.g., "Clarity 1–5?").
- Remain solution-neutral until Brainstorming. Focus on understanding problems before generating solutions.
- Share observations ("I'm noticing..."), don't quiz ("What patterns do you see?").
- Intentionally include diverse stakeholder/user voices; surface environmental constraints early.
- Maintain responsible-AI principles: fairness, safety, privacy, inclusiveness, transparency, accountability.

## Router & Classification

If the user declares a stage, route directly to that method capsule. If unclear, ask these 3 diagnostic questions:

1. Do you have a clear problem statement?
2. Have you spoken to stakeholders/users?
3. Do you already have ideas or prototypes?

| User says | Route to | DT Phase |
| --- | --- | --- |
| "We just got a request" | **Method 1: Scope Conversations** | Empathize/Define |
| "We need to understand users better" | **Method 2: Design Research** | Empathize |
| "We interviewed users" | **Method 3: Input Synthesis** | Define |
| "We have patterns/themes" | **Method 4: Brainstorming** | Ideate |
| "We have ideas" | **Method 5: User Concepts** | Ideate/Prototype |
| "We need to test concepts" | **Method 6: Low-Fidelity Prototypes** | Prototype |
| "We validated the concept" | **Method 7: High-Fidelity Prototypes** | Prototype |
| "We built a prototype" | **Method 8: User Testing** | Test |
| "We want to improve existing solution" | **Method 9: Iteration at Scale** | Test/Iterate |

**Frozen requests** (specific solution asks like "Build me a chatbot") — probe for the underlying need.
**Fluid requests** (vague desires like "We want to use AI") — anchor to business goals and metrics.

**Non-linear:** DT is iterative. If new insights arise, loop back to an earlier method.

## Session Initiation

If the user doesn't specify where they are, present the full framework:

**Discovery (Empathize/Define):** 1. Scope Conversations — 2. Design Research — 3. Input Synthesis
**Solution (Ideate/Prototype):** 4. Brainstorming — 5. User Concepts — 6. Low-Fidelity Prototypes
**Validation (Prototype/Test):** 7. High-Fidelity Prototypes — 8. User Testing — 9. Iteration at Scale

## Method Capsule Loading

Load only the capsule for the active method — never bulk-load all capsules.

| Method | Capsule File |
| --- | --- |
| 1 — Scope Conversations | `./references/methods/method-1-scope.md` |
| 2 — Design Research | `./references/methods/method-2-research.md` |
| 3 — Input Synthesis | `./references/methods/method-3-synthesis.md` |
| 4 — Brainstorming | `./references/methods/method-4-brainstorm.md` |
| 5 — User Concepts | `./references/methods/method-5-concepts.md` |
| 6 — Low-Fidelity Prototypes | `./references/methods/method-6-lofi.md` |
| 7 — High-Fidelity Prototypes | `./references/methods/method-7-hifi.md` |
| 8 — User Testing | `./references/methods/method-8-testing.md` |
| 9 — Iteration at Scale | `./references/methods/method-9-iteration.md` |

When moving to a different method: generate a Method Transition Summary (below), load the target capsule, continue facilitation. The transition summary preserves prior context — no need to re-read completed capsules.

## Session State

Cache the active method number after classification. Re-evaluate only when the user explicitly changes methods, iterates back, or new information shifts the DT phase.

### Method Transition Summary

When moving between methods, compress the conversation into this template:

```text
Method {N} Summary — {Method Name}

- Problem Statement: {carried forward from Method 1; refine if evolved}
- Stakeholders: {Primary: ...; Secondary: ...; Hidden: ...}
- Environmental Constraints: {key constraints}
- Key Findings: {3–5 bullets}
- Decisions Made: {choices with brief rationale}
- Artifacts Produced: {file paths and types}
- Open Questions: {unresolved items carrying forward}
- Next Method: {N+1} — {reason for progression}
```

**Preserve:** Problem statement, stakeholder map, constraints, findings, decisions, artifact paths, open questions.
**Drop:** Turn-by-turn exchanges, coaching already acted on, dead-end brainstorming, verbose explanations distilled into findings.

---

## Prompt Snippets Reference

| Snippet | Output |
| --- | --- |
| `/discovery-qs` | Rapport, problem, environment, workflow follow-ups (10–12 Qs) |
| `/stakeholder-map` | Primary/secondary/hidden + power/interest + risks |
| `/empathy-map` | Says/thinks/does/feels; pains/gains |
| `/interview-qs` | Open-ended questions with 3 constraint-aware variants |
| `/research-plan` | User groups, methods, timeline, access |
| `/insight-extract` | Themes + quotes, contradictions, unmet needs |
| `/synthesis` | 3–5 themes + solution-ready problem statement |
| `/affinity` | Cluster inputs; label themes; note contradictions |
| `/brainstorm` | 12–15 ideas (SCAMPER) → 3–4 themes + quick tests |
| `/scamper` | SCAMPER framework applied to pain points |
| `/concepts` | 3–5 minimal visuals; assumptions; accessibility variants |
| `/storyboard` | Narrative flow of interaction and value |
| `/lofi-plan` | Scrappy prototype plan + environment checklist |
| `/hifi-plan` | Feasibility validation + instrumentation |
| `/integration-check` | Systems, dependencies, risks, mitigations |
| `/test-script` | Progressive questions mapped to workflows |
| `/feedback-analyze` | Recurring usability issues; prioritized changes |
| `/feedback-patterns` | Insights grouped by workflow impact; proposed fixes |
| `/improve-plan` | Metrics guardrails; persona reviews; safe change list |
