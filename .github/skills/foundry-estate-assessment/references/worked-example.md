# Worked example

A full, annotated run against the bundled offline fixture
(`tests/fixtures/compliant-estate`). No Azure access is required.

## Run

```bash
cd .github/skills/foundry-estate-assessment
python scripts/foundry_estate_assessment.py scan \
  --fixture tests/fixtures/compliant-estate \
  --output ./demo
```

## The fixture estate

| Resource | Classification | Notes |
| --- | --- | --- |
| `team-a-foundry` | `foundry-current` | AIServices + project management; private networking; project `project-a` on `standard-agent` with VNet injection. |
| `team-b-foundry` | `foundry-classic-hub` | Associated ML workspace; shares team-a's Search service. |
| `central-apim` | `apim` | v2 gateway; exposes `team-a-foundry`; managed-identity to a central Foundry. |
| `team-a-kv` / `team-a-cosmos` / `teamastorage` / `team-a-search` | data services | Entra-only auth, private endpoints; Search referenced by **two** Foundries. |

## What the scan demonstrates

1. **Inventory first.** Two candidate Foundries are discovered and classified before any detailed
   collection; the APIM gateway is discovered too, but is not counted as a Foundry.
2. **Shared peripheral scanned once.** `team-a-search` is referenced by both Foundries yet profiled a
   single time; `peripheral-footprint.csv` records `referencingResourceCount = 2`.
3. **Region de-duplication.** Cosmos reports the same ~42.5 GB of documents in each of two regions;
   the footprint counts it once (aggregated with `max`, not summed to 85 GB).
4. **Relationships are directed and proven.** `FOUNDRY_HAS_PROJECT`, `PROJECT_USES_COSMOS`,
   `FOUNDRY_EXPOSED_THROUGH_APIM` (Foundry → gateway), etc.
5. **`UNKNOWN`, not `FAIL`.** Checks that need central-platform configuration (e.g. central telemetry
   workspace IDs) or evidence that cannot be proven from the control plane (hub/spoke peering, private
   DNS association) resolve to `UNKNOWN` for investigation — never to a failure.
6. **Classic hub is scoped correctly.** `team-b-foundry` yields `NOT_APPLICABLE` for
   `foundry-current` rules and is sized as an `XL` migration because of its architecture.

## Example outputs

`peripheral-footprint.csv` (shared Search fan-in):

```text
resourceType,resourceId,...,referencingResourceCount
search,.../searchServices/team-a-search,...,2
cosmos,.../databaseAccounts/team-a-cosmos,...,1
```

`migration-effort.csv` (drivers, not failed-rule counts):

```text
foundryResourceId,band,confidence,dataGB,drivers,unknownDependencies
.../team-a-foundry,XL,MEDIUM,578.5,"1 projects; 1 model deployments; 47 Search indexes; shared search dependency; 578.5 GB data footprint","network topology / DNS evidence incomplete"
```

## Re-scoring after editing the standard (no Azure)

```bash
# Edit standards/standard-foundry-v1.yaml, then:
python scripts/foundry_estate_assessment.py reevaluate \
  --output ./demo --standard standards/standard-foundry-v1.yaml
```

For example, changing `parameters.expected_foundry_sku` from `S0` to `P0` flips `FND-ACCOUNT-002`
from `PASS` to `FAIL` for `team-a-foundry` — with no code change and no re-collection.

## Interpreting the compliant estate

Even a well-run estate typically shows a mix of `PASS` and `UNKNOWN`: the `UNKNOWN` results are the
**investigation backlog** in `unknowns.csv`, telling you precisely what evidence to gather (or which
central-platform parameters to populate) to reach a confident conclusion. That is the intended
behaviour — the scanner never guesses a `PASS` or manufactures a `FAIL`.
