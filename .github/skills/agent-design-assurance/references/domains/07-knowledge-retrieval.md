# Domain 07 — Data ingestion, knowledge architecture and retrieval

Prefix `KR` · Reconstruct the knowledge lifecycle from source systems to model context.

## Method

1. Trace each source: system → ingestion trigger → transformation/extraction → storage → chunking/embedding → index → retrieval call → context assembly → citation.
2. Index schemas: prefer IaC/JSON definitions in the repo; otherwise authorised `ada.py azure collect` (index **definitions and statistics only**). Never query index documents.
3. Record field names and types; alias field names only if they reveal sensitive business information.
4. Establish explicitly which retrieval pattern is used (KR-13). This is a key decision input; do not presume migration.

## Criteria

| ID | Criterion | Investigate | Typical evidence |
|---|---|---|---|
| KR-01 | Source systems and authority | Each source, its purpose, authority, owner, and whether it is the system of record. | Ingestion config, docs |
| KR-02 | Ingestion pipelines and scheduling | Pipelines (Data Factory, indexers, functions), triggers, schedules, failure handling. | Pipeline JSON, IaC, code |
| KR-03 | Freshness, versioning and change propagation | Update and **deletion** propagation; document versioning; latency from source change to index. | Pipelines, indexer config |
| KR-04 | Document processing and extraction | Parsers, OCR/layout extraction, table extraction and preservation, metadata extraction. | Code, skillsets |
| KR-05 | Permission preservation | Whether source ACLs/permissions are carried into the index and enforced at query time. | Index fields, filters, code |
| KR-06 | Data lineage | Ability to trace a chunk back to source document and version. | Index fields, metadata |
| KR-07 | Index design | Per index: purpose, key, fields (name, type, searchable/filterable/retrievable/sortable/facetable), metadata fields, analyzers, scoring profiles. | Index definition |
| KR-08 | Vector configuration | Vector fields, dimensions, algorithm/profile, compression, semantic configuration. | Index definition |
| KR-09 | Index operations | Indexers, skillsets, population mechanism, document count/size, replicas/partitions. | Azure config, IaC |
| KR-10 | Chunking strategy | Method (fixed, semantic, layout-aware), size, overlap, hierarchy/context metadata, evidence for choice. | Code, skillset |
| KR-11 | Embedding strategy | Embedding model and version, generation mechanism, re-embedding and index migration strategy. | Code, IaC |
| KR-12 | Retrieval mechanics | Lexical/vector/hybrid; semantic ranker; filters; query rewriting/decomposition; top-k; re-ranking; iterative/agentic retrieval; fallback. | Search calls |
| KR-13 | Retrieval access pattern | Direct index queries vs knowledge-base abstraction vs Foundry IQ vs custom orchestration; the contract between agent and knowledge layer. | Code, tool definitions |
| KR-14 | Context construction and citations | How retrieved content becomes model context; ordering, truncation, citation/grounding references returned to users. | Code |
| KR-15 | Retrieval evaluation | Recall/precision measurement, test queries, ground truth, results. | Eval code, datasets |

## Index capture template (per index, in `technical_details` + `search_index` entity `properties`)

`purpose`, `field_count`, `key_field`, `fields[] {name, type, searchable, filterable, retrievable, sortable, facetable, vector_dimensions}`, `vector_profiles`, `semantic_configurations`, `scoring_profiles`, `analyzers`, `indexers`, `skillsets`, `population`, `document_count`, `storage_size`, `replicas`, `partitions`.

## Stance

Collect enough evidence to later judge whether knowledge-base-mediated retrieval would add value **or** add unwanted complexity. Record why the current contract was chosen, if documented.

## Signals → targeted questions

- No deletion propagation → ask what happens to answers grounded in withdrawn documents.
- Fixed-size chunking on table-heavy financial documents → ask how table integrity is preserved.
- Retrieval implemented directly against an index → ask why that contract was chosen and how query strategies are tested.
- Embedding model pinned with no re-embedding plan → ask about model retirement impact on the index.
