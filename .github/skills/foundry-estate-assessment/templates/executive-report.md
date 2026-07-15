# Executive report template

Use this structure to turn the scanner's deterministic outputs (`reports/`) into an executive
narrative. Fill every placeholder from the CSV/JSON/Markdown the scanner produced — do **not**
invent numbers. Frame `FAIL` results as constructive improvement recommendations.

---

## Azure AI Foundry Estate Assessment — Executive Summary

**Scope:** {scope label from executive-summary.md}
> Note: `all-accessible` means every subscription readable by the assessing identity, **not**
> tenant-wide. {N} subscriptions were readable; {M} were not and are listed as coverage gaps.

**Standard:** {standard id + version} · **Assessed:** {date} · **Scanner:** {version}

### At a glance

- Foundries discovered: {count} ({current} current, {classic} classic hub, {other} other).
- Pattern adherence: {PASS}/{total assessed} rules adherent; {UNKNOWN} require investigation.
- Migration effort: {S}/{M}/{L}/{XL} distribution.
- Largest footprints: {top foundries by GB}.

### Adherence to the standard

Summarize by area (account, networking, bring-your-own-data, gateway, authentication,
observability). For each material `FAIL`, state the improvement recommendation and its business
rationale. Reference `findings.csv`.

### Investigation backlog (unknowns)

The most impactful `UNKNOWN` results and what evidence or central-platform configuration would
resolve them. Reference `unknowns.csv`. Do not present unknowns as failures.

### Accepted transitional patterns

List any `ACCEPTED_EXCEPTION` results and transitional patterns (e.g. team-to-APIM API-key
authentication) with their rationale and, where applicable, expiry. These are accepted, time-boxed
deviations — not endorsed end states.

### Migration / upgrade effort

Explain the band distribution and the top drivers (from `migration-effort.csv`). Stress that effort
is independent of compliance and that data footprint uses de-duplicated regional metrics.

### Coverage and confidence

- Subscriptions and resources covered vs. gaps.
- Confidence levels for effort estimates and what would raise them.

### Recommended next steps

Prioritized, constructive actions tied to specific findings and unknowns.

---

Machine-readable evidence backing this summary: `foundries.csv`, `findings.csv`, `unknowns.csv`,
`relationships.csv`, `peripheral-footprint.csv`, `migration-effort.csv`, `estate.json`.
