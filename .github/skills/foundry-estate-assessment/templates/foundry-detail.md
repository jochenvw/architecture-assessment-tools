# Foundry detail template

One section per Foundry, populated from `foundries.csv`, `findings.csv`, `unknowns.csv`,
`relationships.csv`, and `migration-effort.csv`. Keep the held-back, constructive voice: explain the
*why* behind each recommendation.

---

## {Foundry display name}

- **Resource ID:** `{id}`
- **Classification:** {foundry-current | foundry-classic-hub | ...}
- **Subscription / region:** {sub} / {region}
- **Rollup result:** {PASS | FAIL | UNKNOWN} — {one-line reason}

### Architecture

Describe generation (current vs. classic hub), project/deployment counts, and networking posture
(public/private, VNet injection, private endpoints). Note classic-hub rules marked
`NOT_APPLICABLE` where relevant.

### Findings by area

| Rule | Area | Result | Notes |
| --- | --- | --- | --- |
| {rule id} | {area} | {result} | {evidence-based note} |

Group by account, networking, data, gateway, authentication, observability. For each `FAIL`, give
the improvement recommendation and the reason it matters. For each `UNKNOWN`, state what evidence is
missing.

### Dependencies

From `relationships.csv`: projects, model deployments, connected data services (Key Vault, Cosmos,
Storage, Search), gateway exposure, and any shared or cross-subscription dependencies. Flag shared
peripherals (e.g. a Search service used by multiple Foundries).

### Migration / upgrade effort

- **Band / confidence:** {band} / {confidence}
- **Data footprint:** {GB} (regionally de-duplicated)
- **Drivers:** {drivers}
- **Unknown dependencies:** {list}

Explain what drives the band and what would raise confidence.

### Recommended actions

Prioritized, constructive next steps for this Foundry, each tied to a specific finding or unknown.
