# Evidence model

Every fact the scanner records is **sanitized, provenanced and normalized** before it is stored or
evaluated. The database under `<output>/assessment.db` is the durable source of truth.

## Evidence flow

```text
Azure CLI JSON ──► sanitize() ──► normalized fact  ──► SQLite (evidence table)
                        │                              
                        └──────► sanitized raw JSON ──► <output>/raw/*.json  (unless --no-raw-evidence)
                                        │
                                        └──► SHA-256 provenance hash (always computed)
```

- **Normalized fact:** the small, rule-relevant projection a collector extracts (e.g. `kind`,
  `publicNetworkAccess`, `disableLocalAuth`, footprint counts). This is what rules read.
- **Raw evidence:** the sanitized full response, written atomically (temp file + `fsync` + replace)
  so an interrupt never leaves a partial file. Skipped entirely with `--no-raw-evidence`, but the
  hash is still computed for change detection.
- **Collection status:** each evidence row records `SUCCEEDED`, `PARTIAL`, `BLOCKED_PERMISSION`,
  `BLOCKED_NETWORK`, `UNSUPPORTED`, `UNKNOWN` or `ERROR`. Rules use this to decide `UNKNOWN`.

## Sanitization

`sanitize.py` deep-copies and redacts before anything leaves memory:

- **Secret-bearing keys** (case-insensitive substring): `password`, `secret`, `apikey`, `accountkey`,
  `primary/secondarykey`, `connectionstring`, `authorization`, `sastoken`, `accesskey`,
  `clientsecret`, `privatekey`, `subscriptionkey`, Key Vault `value`, `token`, `credential`, etc.
- **Inline secrets in strings:** SAS `sig=`/`signature=` query parameters, `Bearer` tokens, and
  `AccountKey=`/`SharedAccessKey=` connection-string fragments.
- **Safe look-alikes** such as `tokenLimit` and `tokenCredential` are preserved.

The input object is never mutated. Tests assert no secret markers ever appear in persisted files or
stored facts.

## Relationships

Edges between resources are recorded with an **evidence type** and a **confidence**:

- `confidence = PROVEN` — established from an authoritative signal (resource id in a connection, a
  diagnostic setting, an APIM backend/policy).
- `confidence = INFERRED` — established from a weaker signal (naming, tags, topology heuristics).

Examples: `FOUNDRY_HAS_PROJECT`, `PROJECT_USES_COSMOS`, `PROJECT_USES_SEARCH`,
`FOUNDRY_EXPOSED_THROUGH_APIM`, `APIM_TARGETS_CENTRAL_FOUNDRY`,
`RESOURCE_SENDS_TELEMETRY_TO_WORKSPACE`. A shared data service records **fan-in**
(`referencingResourceCount`) so shared dependencies are visible and scanned only once.

## SQLite schema (tables)

| Table | Holds |
| --- | --- |
| `schema_meta` | Schema version. |
| `assessment_runs` | Run metadata: scope, identity, standard, versions. |
| `inventory_snapshots` | Stable snapshots (the progress denominator). |
| `subscriptions` | Per-snapshot subscription accessibility. |
| `resources` | Discovered resources + classification + properties. |
| `relationships` | Directed edges with evidence type + confidence. |
| `tasks` | Collector tasks: status, attempts, lease, retry timing (resume state). |
| `evidence` | Normalized facts + provenance (path, hash, api version, status). |
| `metrics` | Footprint metrics (counts, sizes) with timestamps. |
| `findings` | Rule results with expected/actual/explanation/effective result. |
| `effort_estimates` | Deterministic migration bands + drivers. |

## Change detection

Because each evidence row carries a SHA-256 of its sanitized raw response, a `refresh` can detect
whether a resource's configuration changed between snapshots without re-reading secrets.
