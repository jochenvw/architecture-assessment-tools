# Rule authoring

The standard is a single YAML file (`standards/standard-foundry-v1.yaml`). It is **meant to be
edited**. You can clone it, add rules, change parameters, or add exceptions — then `reevaluate` to
re-score already-collected evidence with **no Azure calls** and no code changes.

## File structure

```yaml
metadata:      # id, version, description, status
parameters:    # named values referenced by *_parameter operators
effort:        # weights + band thresholds (see migration-sizing.md)
rules:         # the rule catalogue
exceptions:    # time-boxed accepted deviations
```

## Anatomy of a rule

```yaml
- id: FND-NET-001
  title: Foundry has an approved private endpoint
  category: networking
  severity: high                 # info | low | medium | high (configurable per rule)
  applies_to: [foundry-current]  # resource classifications this rule targets
  evidence:
    path: networking.foundryPrivateEndpointPresent   # collector.fact-field
  assertion:
    equals: true
  recommended_investigation: >
    Optional guidance shown for FAIL/UNKNOWN results.
```

- `applies_to` uses classifications: `foundry-current`, `foundry-classic-hub`,
  `azure-openai-account`, `ai-services-account`, `unknown-cognitive-account`. A rule that does not
  target a resource yields `NOT_APPLICABLE`.
- `evidence.path` is `collector.field`; the collector names match `collectors/` modules (e.g.
  `foundry`, `projects`, `connections`, `networking`, `observability`).

## Scalar operators

| Operator | Passes when | Missing evidence |
| --- | --- | --- |
| `equals: X` | value == X | `UNKNOWN` |
| `equals_parameter: P` | value == `parameters[P]` | `UNKNOWN` |
| `in: [..]` / `in_parameter: P` | value in list | `UNKNOWN` |
| `contains: X` / `contains_parameter: P` | list contains X | `UNKNOWN` |
| `exists: true/false` | presence matches | `UNKNOWN` |
| `not_exists: true/false` | absence matches | `UNKNOWN` |
| `greater_than: N` / `less_than: N` | numeric comparison | `UNKNOWN` |
| `count_equals: N` / `count_greater_than: N` | length/int comparison | `UNKNOWN` |

Missing evidence, or a value that is literally `"unknown"`/`"unavailable"`/`"not-collected"`, always
yields `UNKNOWN` — **never** `FAIL`.

## Relationship operators

For rules about connected resources (data services, gateway):

```yaml
assertion:
  relationship_exists: [PROJECT_USES_KEYVAULT]     # PASS if an edge of this type exists
```

```yaml
assertion:
  all_related_resources_match:                     # every related resource must match
    relationship_types: [PROJECT_USES_COSMOS]
    path: disableLocalAuth        # bare field, or collector-prefixed (e.g. apim.isV2)
    equals: true
```

`any_related_resource_matches` passes if **any** related resource matches. Related-resource fields
can be addressed either bare (`disableLocalAuth`) or collector-prefixed (`apim.isV2`). If no related
resources were collected, the result is `UNKNOWN`. `relationship_exists` returns `UNKNOWN` (not
`FAIL`) when no evidence has been collected for the Foundry yet.

## Parameters

Reference organisation-specific values without hard-coding them in rules:

```yaml
parameters:
  expected_foundry_sku: S0
  accepted_team_to_apim_authentication: [api-key]
  central_apim_resource_ids: []      # empty ⇒ centralization rules resolve to UNKNOWN, not FAIL
```

Populating `central_*_resource_ids` lets gateway/telemetry-centralization rules assess against your
platform resources; leaving them empty keeps those rules at `UNKNOWN` rather than failing.

## Exceptions

Turn a known, accepted `FAIL` into an `ACCEPTED_EXCEPTION` without hiding it:

```yaml
exceptions:
  - id: EXC-2026-001
    resource_id: /subscriptions/.../accounts/team-x-foundry
    rule_ids: [FND-NET-002]
    reason: Public access retained until private-link migration completes.
    expires_on: 2026-12-31        # expired exceptions no longer apply
```

The underlying result stays visible; the effective result becomes `ACCEPTED_EXCEPTION` until the
expiry date passes.

## Authoring checklist

1. Pick a stable `id` (`FND-<AREA>-NNN`) and clear `title`.
2. Set `applies_to` to the right classification(s).
3. Choose the smallest evidence path that proves the point.
4. Prefer `*_parameter` operators so the rule stays organisation-agnostic.
5. Write `recommended_investigation` as constructive guidance.
6. `reevaluate` against the fixture or a real run and confirm the result is what you expect.
