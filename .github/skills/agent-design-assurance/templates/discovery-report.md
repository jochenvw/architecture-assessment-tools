# Design assurance discovery report: {{application alias}}

> Internal discovery output for independent architectural review. Not a final
> assessment. Every statement cites evidence IDs (`EV-…`) from `evidence.json`;
> anything without evidence is labelled **unknown**, **briefing (unverified)** or
> **inferred**.

## 1. Application overview

{{Purpose, users, business process supported, criticality. Cite EV-IDs.}}

## 2. Discovery scope and limitations

| Item | Value |
| --- | --- |
| Profiles | {{profile ids}} |
| Discovery modes | {{repository / azure_configuration / azure_telemetry / interview}} |
| Repository revision | {{revision, working-tree state}} |
| Environments inspected | {{environments}} |
| Evidence sources unavailable | {{sources and reason}} |

{{Limitations that materially affect confidence.}}

## 3. Current implementation and maturity

{{Implementation stage, what runs where, coverage vs maturity headline (from discovery-coverage.json).}}

## 4. Known challenges and outstanding work

{{Only items documented by the team (issues, TODO markers, ADRs). No speculation.}}

## 5. Architecture

### 5.1 Infrastructure architecture

{{Azure resources by alias, regions, environments. Diagram reference.}}

### 5.2 Logical application architecture

{{Components, responsibilities, interfaces.}}

### 5.3 Agent architecture and execution

{{Agents, tools, orchestration pattern, model deployments, execution flows (FLOW-IDs).}}

### 5.4 Knowledge and data architecture

{{Sources, ingestion, storage, indexes, retrieval path.}}

### 5.5 Network and identity architecture

{{Ingress, egress, private endpoints, identities, RBAC.}}

## 6. Findings by discovery domain

Per domain: what was investigated, what was found, coverage, maturity range,
key evidence, unknowns.

### Domain 01: Business context and workload characteristics

{{findings}}

### Domain 02: Microsoft technology stack and current capability alignment

{{findings}}

### Domain 03: Azure infrastructure and Well-Architected principles

{{findings}}

### Domain 04: Customer platform standards

{{findings}}

### Domain 05: Software engineering and application architecture

{{findings}}

### Domain 06: Agent architecture, orchestration and model strategy

{{findings}}

### Domain 07: Data ingestion, knowledge architecture and retrieval

{{findings}}

### Domain 08: Functional assurance, correctness and human oversight

{{findings}}

### Domain 09: Evaluations, guardrails and behavioural assurance

{{findings}}

### Domain 10: Security, identity and data governance

{{findings}}

### Domain 11: Observability, reliability, scalability and economics

{{findings}}

### Domain 12: Lifecycle, traceability and operational ownership

{{findings}}

## 7. Existing strengths

{{OBS-IDs classified as strength, with evidence.}}

## 8. Potential gaps and implications

{{OBS-IDs classified as potential gap: implementation, implication, follow-up question. Constructive wording.}}

## 9. Architectural decisions and rationale

{{DD-IDs from design-decisions.json; documented vs inferred rationale.}}

## 10. Workload and runtime characteristics

{{WL-IDs: declared vs measured values, units, sources.}}

## 11. Unknowns and conflicting evidence

{{Criteria with maturity U, conflicting evidence, briefing claims not verified.}}

## 12. Questions for the development team

See `open-questions.md` (prioritised). Top questions:

{{Q-IDs P1}}
