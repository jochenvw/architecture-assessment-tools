# Information protection

Assume the repository and Azure environment contain confidential material. The package must be
safe to hand to an external architect after the team's own review.

## 1. Never export

| Category | Instead |
|---|---|
| Secrets, keys, tokens, connection strings with credentials | Describe the auth mechanism ("API key from app setting") |
| Raw documents, business data, index contents | Describe schema and classification |
| Financial figures, unpublished results | "a revenue figure", "a materiality threshold" |
| PII (names, emails, phone numbers, IDs) | Roles ("platform owner", "reviewer") |
| Prompt and response text | Purpose, inputs, structure, loading mechanism |
| Proprietary source excerpts | Semantic description + repo-relative location |
| Raw logs | Aggregates only |
| Real resource names, IDs, hosts, IPs, tenant or subscription IDs | Consistent aliases |

## 2. Mechanism

```text
ada.py sanitize --out P            # scan: list findings, change nothing
ada.py sanitize --out P --apply    # redact secrets, alias identifiers, report manual-review items
ada.py check --out P               # sanitize scan is one of the gates
ada.py package --out P             # re-scans before zipping; refuses on any finding
```

| Rule kind | Severity | `--apply` action |
|---|---|---|
| `private_key`, `connection_string_secret`, `sas_signature`, `jwt`, `bearer_token`, `github_token`, `aws_access_key`, `azure_key_base64`, `generic_secret_assignment` | secret | `[REDACTED-…]` |
| `arm_resource_id`, `azure_host`, `guid`, `email`, `public_ipv4` | identifier | Stable alias (`AZ-SUB-1`, `AZ-RG-1`, `AZ-SEARCH-1`, `az-host-1.…`, …) |
| Known resource names collected from Azure | identifier | Same alias as the collector used |
| Registered internal names (known terms) in any text | identifier | Alias by kind: `APP-n`, `ORG-n`, `TEAM-n`, `SYSTEM-n`, `PERSON-n`, `TERM-n` |
| `financial_figure` | manual_review | **Never auto-fixed.** Rewrite, or allowlist with a reason |

Aliases are consistent across all files, so relationships remain readable. The alias map
(`_work/alias-map.json`) is the only link back to real values. It never leaves `_work/`, and
`_work/` is never packaged.

**Known terms** are replaced first, case-insensitively, wherever they appear (prose included).
Names under 4 characters and well-known public names (Microsoft, Azure, GitHub, …) are ignored.
They are registered automatically:

| Source | When | Alias |
|---|---|---|
| Repository name and remote URL segments (GitHub, Azure DevOps) | `init` | `APP-n` (repo), `ORG-n` (org, project) |
| Resource-group name, subscription name | `azure collect` | `AZ-RG-n`, `AZ-SUB-n` |
| Resource names | `azure collect` | `AZ-<TYPE>-n` |

Anything else that could identify the organisation (product, customer, team, internal system or
codename found in the repo) must be registered by the agent before `sanitize`:

```text
ada.py alias --out P --term "<name>" --kind SYSTEM    # repeat --term; --list shows the map locally
```

If a registered name still appears unaliased, `check` fails (`sensitive-identifier`) until
`sanitize --apply` runs.

## 3. False positives

Allowlist in `_work/sanitize-allowlist.json`:

```json
{"allow": [{"match": "2024-07-01", "reason": "API version, not a date of business significance", "file": "technology-inventory.json"}]}
```

`file` is optional. Every entry needs a reason. Keep the list short. A long allowlist means the
descriptions are too verbatim.

## 4. Exclusions

If something cannot be reliably sanitised, remove it from the package and add a `limitations`
entry to the manifest saying what was excluded and why. The manifest `sanitisation` block records
`performed_at`, `secrets_redacted`, `aliases_applied`, `allowlisted`, `files_excluded` and
`manual_review_notes`.

## 5. Repository safety

- `init` skips secret-bearing files (`.env`, `*.pfx`, `*.key`, …; `.env.example` is allowed). It
  records only their existence.
- The repository is never written to. The package folder has its own `.gitignore` (`*`).
- `init` snapshots `git status`. `check` and `package` fail with `repository-modified` if the
  working tree changed.

## 6. Team review before handover

The development team opens the ZIP, reads every file (all are text), and confirms it contains
nothing they would not share. Only they hand it over.
