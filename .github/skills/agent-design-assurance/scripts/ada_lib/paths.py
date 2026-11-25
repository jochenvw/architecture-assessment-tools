"""Well-known locations inside the skill and inside an output package."""

from __future__ import annotations

from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = SKILL_ROOT / "schemas"
PROFILES_DIR = SKILL_ROOT / "profiles"
DOMAINS_DIR = SKILL_ROOT / "references" / "domains"
TEMPLATES_DIR = SKILL_ROOT / "templates"

WORK_DIR_NAME = "_work"
DIST_DIR_NAME = "_dist"

# Package file -> schema file. Markdown/CSV files are listed separately.
JSON_FILES = {
    "manifest.json": "manifest.schema.json",
    "evidence.json": "evidence.schema.json",
    "assessment.json": "assessment.schema.json",
    "architecture.json": "architecture.schema.json",
    "execution-flows.json": "execution-flows.schema.json",
    "technology-inventory.json": "technology-inventory.schema.json",
    "workload-characteristics.json": "workload-characteristics.schema.json",
    "design-decisions.json": "design-decisions.schema.json",
    "discovery-coverage.json": "discovery-coverage.schema.json",
    "azure-configuration.json": "azure-configuration.schema.json",
}

AUTHORED_MARKDOWN = [
    "README.md",
    "discovery-report.md",
    "executive-discovery-summary.md",
]

RENDERED_FILES = [
    "assessment.csv",
    "preliminary-observations.csv",
    "open-questions.md",
    "discovery-coverage.json",
]

REQUIRED_FILES = sorted(set(JSON_FILES) | set(AUTHORED_MARKDOWN) | set(RENDERED_FILES))

DOMAIN_TITLES = {
    "01": "Business context and workload characteristics",
    "02": "Microsoft technology stack and current capability alignment",
    "03": "Azure infrastructure and Well-Architected principles",
    "04": "Customer platform standards",
    "05": "Software engineering and application architecture",
    "06": "Agent architecture, orchestration and model strategy",
    "07": "Data ingestion, knowledge architecture and retrieval",
    "08": "Functional assurance, correctness and human oversight",
    "09": "Evaluations, guardrails and behavioural assurance",
    "10": "Security, identity and data governance",
    "11": "Observability, reliability, scalability and economics",
    "12": "Lifecycle, traceability and operational ownership",
}
