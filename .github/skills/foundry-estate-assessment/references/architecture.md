# Architecture

The scanner is a small Python package with clean module boundaries. Each module has one concern and
is independently testable. Azure access is injected so the whole pipeline runs offline against a
fixture.

## Pipeline

```text
doctor ─┐
        ▼
   inventory ──►  scan phases  ──►  evaluate  ──►  report
   (snapshot)     (collectors)      (rules)        (deterministic files)
                      │                                  ▲
                      ▼                                  │
                  SQLite state  ◄──────── resume / reevaluate
```

1. **Preflight (`doctor`)** — identity (`az account show`), CLI version, and which subscriptions in
   the requested scope are readable.
2. **Inventory** — Azure Resource Graph enumerates candidate cognitive-services accounts and APIM
   gateways, classifies each account, and writes a **stable snapshot**. This snapshot is the
   denominator for all progress reporting; detailed work never starts before it completes.
3. **Collection** — the scheduler runs collectors as checkpointed tasks:
   - **Foundry phase:** one task per collector per Foundry (`foundry`, `projects`,
     `model-deployments`, `connections`, `networking`, `observability`).
   - **Peripheral phase:** shared data services (Key Vault, Cosmos, Storage, Search) and the APIM
     gateway are profiled **once each** even when referenced by several Foundries.
4. **Evaluation** — the rule engine scores collected evidence against the standard. It performs **no
   Azure calls**, so `reevaluate` can re-run a changed standard against old evidence.
5. **Effort** — deterministic migration sizing from drivers (see `migration-sizing.md`).
6. **Reporting** — stable CSV/JSON/Markdown.

## Modules

| Module | Concern |
| --- | --- |
| `api_versions.py` | Centralized Azure REST API versions. |
| `models.py` | Enums and dataclasses shared across the scanner. |
| `azure_cli.py` | `CommandRunner` (subprocess / fixture), `AzureClient`, typed errors. |
| `sanitize.py` | Redact secrets from any evidence before it is persisted or evaluated. |
| `database.py` | SQLite schema + DAO. Thread-safe: all access is serialized under one lock. |
| `inventory.py` | Resource Graph discovery + classification. |
| `scheduler.py` | Bounded-concurrency, resumable, leased task execution; `Ctrl+C` handling. |
| `evidence.py` | Normalized evidence + sanitized raw-file persistence with SHA-256 provenance. |
| `rules.py` | YAML load, assertion operators, evaluation (`PASS/FAIL/UNKNOWN/NA/ERROR`). |
| `effort.py` | Driver-based migration sizing bands. |
| `reporting.py` | Deterministic reports. |
| `cli.py` | Commands + orchestration + argument parsing. |
| `collectors/*` | One evidence gatherer per concern. |
| `yaml_lite.py` | PyYAML when available, else a bundled minimal loader (zero deps). |

## Concurrency model

The scheduler uses a `ThreadPoolExecutor`. All collectors share a single SQLite connection opened
with `check_same_thread=False`; **every** read and write is serialized through one re-entrant lock in
`database.py` (`transaction`, `_fetchall`, `_fetchone`). New DAO methods must use these helpers — an
unguarded read racing a write causes intermittent task failures.

## Offline testability

`azure_cli.py` defines a `CommandRunner` protocol. `SubprocessCommandRunner` runs the real `az` CLI
(argument arrays, never `shell=True`). `FixtureCommandRunner` serves canned responses from an
`estate.json` file, dispatching by command shape and longest-substring URL match. Every test and the
`--fixture` flag use this path, so the full pipeline is exercised with zero Azure access.

## Failure classification

`az` failures are classified into typed exceptions (`Authentication`, `Authorization`, `Network`,
`Throttling`, `UnsupportedApi`, `MalformedResponse`) which the scheduler maps to precise task states
(`BLOCKED_PERMISSION`, `BLOCKED_NETWORK`, `RETRYABLE_ERROR`, `UNSUPPORTED`, `FAILED`). Blocked and
retryable work is resumable; a permission gap becomes an `UNKNOWN` in the report, never a `FAIL`.
