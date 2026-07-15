# Migration sizing

Migration / upgrade effort is a **separate axis** from compliance. A fully adherent Foundry can still
be `XL` to move because of its data footprint, and a non-adherent one can be `S`. Effort is computed
deterministically from **drivers**, never from the number of failed rules.

## Bands

| Band | Meaning |
| --- | --- |
| `S` | Small — mostly configuration recreation. |
| `M` | Medium — moderate footprint or a few dependencies. |
| `L` | Large — significant data footprint or shared/cross-subscription dependencies. |
| `XL` | Extra-large — classic-hub re-platforming and/or heavy data movement. |
| `UNKNOWN` | Core evidence (the Foundry itself) could not be collected. |

Bands come from a numeric score compared against configurable thresholds:

```yaml
effort:
  bands: { S: 10, M: 30, L: 60 }   # score <=S ⇒ S, <=M ⇒ M, <=L ⇒ L, else XL
```

## Drivers and weights

Each driver adds to the score. All weights are configurable under `effort.weights`:

| Driver | Default weight | Rationale |
| --- | --- | --- |
| `classic_hub` | 40 | Classic hub re-platforming is the dominant cost. |
| `per_project` | 4 | Each project is a unit of reconfiguration. |
| `per_deployment` | 1 | Model deployments must be recreated/re-pointed. |
| `data_gb_per_100` | 6 | Data movement scales with footprint (per 100 GB). |
| `per_search_index_10` | 3 | Search index rebuild/reindex effort (per 10 indexes). |
| `shared_dependency` | 8 | A data service shared by multiple Foundries complicates cut-over. |
| `cross_subscription_dependency` | 6 | Cross-subscription dependencies add coordination. |
| `networking_unknown` | 4 | Incomplete topology/DNS evidence adds risk. |
| `private_endpoint_missing` | 6 | Adding private networking is real work. |

Every estimate lists the concrete drivers that produced it (e.g. `1 projects; 47 Search indexes;
shared search dependency; 578.5 GB data footprint`).

## Data footprint (no double counting)

Data footprint sums the true stored size of each connected data service. Metrics that Azure reports
**per replicated region** (notably Cosmos DB storage) are aggregated with `max`, not `sum`: two
regions holding the same 42.5 GB count as 42.5 GB, not 85 GB.

## Confidence

Confidence reflects how much evidence was available, independent of the band:

| Confidence | When |
| --- | --- |
| `HIGH` | Core and dependency evidence complete. |
| `MEDIUM` | Some non-core evidence missing (e.g. topology). |
| `LOW` | Core Foundry evidence missing, or three or more unknown dependencies. |

`unknown_dependencies` on each estimate lists exactly what was missing, so a `MEDIUM`/`LOW` estimate
tells you what to collect to firm it up.

## Tuning

Because weights and bands live in the standard YAML, an organisation can recalibrate sizing to its
own experience (e.g. raise `classic_hub` if hub migrations proved harder) and `reevaluate` without
touching code.
