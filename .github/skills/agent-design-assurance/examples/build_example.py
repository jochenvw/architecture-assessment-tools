"""Regenerate examples/contoso-claims-review through the real CLI (fictional data).

Usage: python examples/build_example.py
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
ADA = SKILL / "scripts" / "ada.py"
DEST = SKILL / "examples" / "contoso-claims-review"
TS = "2025-01-15T10:00:00Z"
PROFILES = "azure-agent,example-platform,example-document-review"

tmp = Path(tempfile.mkdtemp())
repo = tmp / "contoso-claims-review"
out = tmp / "out"
files = {
    "README.md": "# Contoso claims reviewer\nReviews insurance claim summaries for numeric consistency.\n",
    "requirements.txt": "azure-ai-projects==1.0.0\nazure-identity==1.19.0\nopenai==1.58.1\nopentelemetry-sdk==1.29.0\n",
    "src/claims_review/app.py": "# FastAPI entry point\n",
    "src/claims_review/orchestrator.py": "# Orchestrator\n",
    "src/claims_review/prompts/reviewer.md": "You are a reviewer.\n",
    "infra/main.bicep": "// infra\n",
    "docs/adr/0002-agent-framework.md": "# ADR 2\n",
}
for rel, text in files.items():
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
for cmd in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "-c", "user.name=example", "-c", "user.email=example@example.invalid", "commit", "-qm", "init"]):
    subprocess.run(cmd, cwd=repo, check=True)


def ada(*args, ok=(0,)):
    r = subprocess.run([sys.executable, str(ADA), *args], capture_output=True, text=True)
    print(r.stdout[-3000:], r.stderr[-3000:])
    if r.returncode not in ok:
        raise SystemExit(f"ada {args[0]} failed {r.returncode}")
    return r


ada("init", "--repo", str(repo), "--out", str(out), "--profiles", PROFILES)
load = lambda n: json.loads((out / n).read_text(encoding="utf-8"))
def dump(n, d): (out / n).write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

# ---------------------------------------------------------------- evidence
def ev(id, crit, st, cls, persp, desc, path=None, lines=None, env="not_applicable", **kw):
    e = {"id": id, "criteria": crit, "source_type": st, "classification": cls, "perspective": persp,
         "description": desc, "environment": env, "discovered_at": TS}
    if path:
        e["location"] = {"path": path, "lines": lines}
        if "symbol" in kw:
            e["location"]["symbol"] = kw.pop("symbol")
    e.update(kw)
    return e

E = [
    ev("EV-README-PURPOSE", ["BC-01"], "documentation", "documented", "declared",
       "README states the application reviews claim summaries for numeric consistency before adjuster sign-off.", "README.md", "1-2"),
    ev("EV-REQ-SDKS", ["MT-02", "MT-04", "SE-04"], "dependency_manifest", "observed", "implemented",
       "requirements.txt pins azure-ai-projects, azure-identity, openai and opentelemetry-sdk to exact versions.", "requirements.txt", "1-4"),
    ev("EV-ORCH-LOOP", ["AE-01", "AE-04", "MT-04"], "source_code", "observed", "implemented",
       "Orchestrator runs a fixed three-stage pipeline (extract, verify, summarise); each stage is one model call with a typed output schema.",
       "src/claims_review/orchestrator.py", "12-88", symbol="ReviewPipeline.run"),
    ev("EV-ORCH-ENUM", ["FA-03", "WRK-01"], "source_code", "observed", "implemented",
       "Claim enumeration is a single model call returning a list; no deterministic cross-check of the count against the source table cells.",
       "src/claims_review/orchestrator.py", "30-52", symbol="extract_claims"),
    ev("EV-ORCH-NUMERIC", ["WRK-02"], "source_code", "observed", "implemented",
       "Numeric comparison uses Decimal arithmetic with an explicit tolerance after the model extracts both values.",
       "src/claims_review/orchestrator.py", "54-71", symbol="compare_values"),
    ev("EV-ADR-FRAMEWORK", ["MT-04"], "adr", "documented", "declared",
       "ADR 0002 selects the Foundry Agent Service SDK over a bespoke loop to reduce hosting effort; alternatives listed.",
       "docs/adr/0002-agent-framework.md", "1-40"),
    ev("EV-PROMPT-FILE", ["LT-03"], "prompt", "observed", "implemented",
       "Reviewer instructions live in a versioned Markdown file loaded at start-up; no runtime override path found.",
       "src/claims_review/prompts/reviewer.md", "1-60"),
    ev("EV-BICEP-PE", ["PLT-01", "WA-02"], "iac", "observed", "declared",
       "Bicep declares private endpoints for the Foundry account and storage; AI Search has publicNetworkAccess enabled.",
       "infra/main.bicep", "40-112"),
    ev("EV-BICEP-MI", ["PLT-02", "SG-02"], "iac", "observed", "declared",
       "Container app uses a user-assigned managed identity with Cognitive Services User and Storage Blob Data Reader roles.",
       "infra/main.bicep", "120-168"),
    ev("EV-APP-CRED", ["PLT-02", "SG-02"], "source_code", "observed", "implemented",
       "Clients are constructed with DefaultAzureCredential; no API keys are read from configuration.",
       "src/claims_review/app.py", "8-21"),
    ev("EV-CONFIG-SETTINGS", ["SE-03"], "configuration", "observed", "implemented",
       "Settings are loaded from environment variables through a typed settings class with startup validation.",
       "src/claims_review/app.py", "23-40", symbol="Settings"),
    ev("EV-OTEL-SPANS", ["OS-02"], "source_code", "observed", "implemented",
       "Each pipeline stage opens an OpenTelemetry span with GenAI attributes; prompt and completion content recording is disabled.",
       "src/claims_review/orchestrator.py", "90-118"),
    ev("EV-NO-EVALS", ["EG-01"], "test", "observed", "implemented",
       "Searched tests, CI workflows and docs for evaluation code, datasets or results; only unit tests for parsing exist.",
       "tests", None, confirms_absence=True),
    ev("EV-AZ-SEARCH-1", ["WA-02", "PLT-01"], "azure_resource_config", "observed", "deployed",
       "Deployed search service (test) has publicNetworkAccess Enabled and zero private endpoint connections.",
       env="test", azure_resource={"alias": "AZ-SEARCH-1", "type": "Microsoft.Search/searchServices", "location": "westeurope"},
       command_template="az resource show --ids {resource_id} --query <per-type projection>"),
    ev("EV-AZ-FOUNDRY-1", ["PLT-01", "PLT-02", "MT-02"], "azure_resource_config", "observed", "deployed",
       "Deployed Foundry account (test) has disableLocalAuth true, publicNetworkAccess Disabled and one private endpoint.",
       env="test", azure_resource={"alias": "AZ-FOUNDRY-1", "type": "Microsoft.CognitiveServices/accounts", "location": "westeurope"},
       command_template="az resource show --ids {resource_id} --query <per-type projection>"),
    ev("EV-BRIEF-CLAIMS", ["WRK-01"], "briefing", "documented", "briefing",
       "Profile briefing claim WRK-B01 states every numeric claim is reviewed; recorded for verification only."),
    ev("EV-INTERVIEW-VOLUME", ["BC-01"], "interview", "documented", "declared",
       "Team lead (role) estimates review volume of a few hundred claim summaries per week; not measured."),
]
dump("evidence.json", {"schema_version": "1.0.0", "evidence": E})

# ---------------------------------------------------------------- assessment
a = load("assessment.json")
DETAIL = {
    "BC-01": dict(status="documented", maturity="3", confidence="medium", discovery_coverage="complete",
                  current_implementation="Reviews claim summaries for numeric consistency before adjuster sign-off.",
                  evidence_refs=["EV-README-PURPOSE", "EV-INTERVIEW-VOLUME"],
                  discovery_attempts=["README", "docs folder", "team interview"]),
    "MT-02": dict(status="observed", maturity="3", confidence="high", discovery_coverage="complete",
                  current_implementation="Foundry project hosts model deployments; SDK azure-ai-projects pinned.",
                  perspectives={"declared": None, "implemented": "SDK used in code", "deployed": "Foundry account in test", "runtime": None},
                  evidence_refs=["EV-REQ-SDKS", "EV-AZ-FOUNDRY-1"], discovery_attempts=["requirements.txt", "Azure resource configuration"]),
    "MT-04": dict(status="observed", maturity="3", confidence="medium", discovery_coverage="complete",
                  current_implementation="Bespoke three-stage pipeline over the Foundry SDK; ADR documents the selection.",
                  design_rationale={"statement": "Reduce hosting effort; alternatives listed in ADR 0002.", "documented": True},
                  conflicting_evidence=[], evidence_refs=["EV-ADR-FRAMEWORK", "EV-ORCH-LOOP", "EV-REQ-SDKS"],
                  discovery_attempts=["ADR folder", "orchestrator source", "dependency manifest"]),
    "WA-02": dict(status="conflicting", maturity="2", confidence="medium", discovery_coverage="complete",
                  current_implementation="Private endpoints for Foundry and storage; search service public.",
                  conflicting_evidence=["Platform baseline expects private networking; deployed search service is public (EV-AZ-SEARCH-1)."],
                  potential_gaps=["AI Search reachable over public network."],
                  evidence_refs=["EV-BICEP-PE", "EV-AZ-SEARCH-1"], discovery_attempts=["Bicep", "Azure resource configuration"]),
    "PLT-01": dict(status="observed", maturity="2", confidence="high", discovery_coverage="complete",
                   current_implementation="Two of three PaaS dependencies are private; AI Search is public.",
                   evidence_refs=["EV-BICEP-PE", "EV-AZ-SEARCH-1", "EV-AZ-FOUNDRY-1"], discovery_attempts=["Bicep", "Azure resource configuration"],
                   risk_severity="medium"),
    "PLT-02": dict(status="observed", maturity="4", confidence="high", discovery_coverage="complete",
                   current_implementation="Managed identity end to end; local auth disabled on the Foundry account.",
                   strengths=["No keys in configuration; disableLocalAuth enforced on the deployed account."],
                   evidence_refs=["EV-BICEP-MI", "EV-APP-CRED", "EV-AZ-FOUNDRY-1"], discovery_attempts=["Bicep", "source", "Azure resource configuration"],
                   assurance_level="enforced"),
    "SG-02": dict(status="observed", maturity="4", confidence="high", discovery_coverage="complete",
                  current_implementation="User-assigned managed identity with least-privilege data-plane roles.",
                  evidence_refs=["EV-BICEP-MI", "EV-APP-CRED"], discovery_attempts=["Bicep", "source"]),
    "SE-03": dict(status="observed", maturity="3", confidence="high", discovery_coverage="complete",
                  current_implementation="Typed settings class validated at start-up.",
                  evidence_refs=["EV-CONFIG-SETTINGS"], discovery_attempts=["source"]),
    "SE-04": dict(status="observed", maturity="3", confidence="high", discovery_coverage="partial",
                  current_implementation="Exact version pins; no lock file or automated update tooling found.",
                  evidence_refs=["EV-REQ-SDKS"], discovery_attempts=["requirements.txt", "searched for dependabot/renovate config"]),
    "AE-01": dict(status="observed", maturity="3", confidence="high", discovery_coverage="complete",
                  current_implementation="Single orchestrator, deterministic three-stage pipeline; no autonomous tool selection.",
                  evidence_refs=["EV-ORCH-LOOP"], discovery_attempts=["source"]),
    "AE-04": dict(status="observed", maturity="3", confidence="high", discovery_coverage="complete",
                  current_implementation="Control flow is code-defined; models fill typed outputs only.",
                  strengths=["Deterministic control flow limits model-driven branching."],
                  evidence_refs=["EV-ORCH-LOOP"], discovery_attempts=["source"]),
    "FA-03": dict(status="observed", maturity="1", confidence="medium", discovery_coverage="complete",
                  current_implementation="Single model call enumerates claims; count not reconciled against the source.",
                  potential_gaps=["No completeness check on enumerated claims."],
                  implications=["Missed claims are silently unreviewed."],
                  evidence_refs=["EV-ORCH-ENUM"], discovery_attempts=["source", "tests"], risk_severity="high"),
    "WRK-01": dict(status="conflicting", maturity="1", confidence="medium", discovery_coverage="complete",
                   current_implementation="Briefing claims exhaustive review; code enumerates via one unchecked model call.",
                   conflicting_evidence=["Briefing WRK-B01 (EV-BRIEF-CLAIMS) vs implementation EV-ORCH-ENUM."],
                   evidence_refs=["EV-ORCH-ENUM", "EV-BRIEF-CLAIMS"], discovery_attempts=["source", "briefing"], risk_severity="high"),
    "WRK-02": dict(status="observed", maturity="3", confidence="high", discovery_coverage="complete",
                   current_implementation="Decimal comparison with explicit tolerance after extraction.",
                   strengths=["Arithmetic is deterministic, not model-judged."],
                   evidence_refs=["EV-ORCH-NUMERIC"], discovery_attempts=["source"], assurance_level="guaranteed_by_construction"),
    "EG-01": dict(status="observed", maturity="0", confidence="high", discovery_coverage="complete", absence_confirmed=True,
                  current_implementation="No evaluation framework, dataset or result found.",
                  evidence_refs=["EV-NO-EVALS"], discovery_attempts=["tests folder", "CI workflows", "docs"], risk_severity="high"),
    "OS-02": dict(status="observed", maturity="3", confidence="high", discovery_coverage="complete",
                  current_implementation="Per-stage OpenTelemetry spans with GenAI attributes; content recording off.",
                  evidence_refs=["EV-OTEL-SPANS"], discovery_attempts=["source"]),
    "LT-03": dict(status="observed", maturity="2", confidence="medium", discovery_coverage="complete",
                  current_implementation="Prompt in Git, versioned with code; no evaluation gate on prompt changes.",
                  evidence_refs=["EV-PROMPT-FILE"], discovery_attempts=["source", "CI workflows"]),
}
NA = {"KR-02": "The application processes uploaded claim summaries only; there is no ingestion pipeline or index refresh (EV-README-PURPOSE)."}
DOMAIN_ATTEMPTS = {
    "01": ["README", "docs folder"], "02": ["dependency manifest", "IaC"], "03": ["IaC", "Azure resource configuration"],
    "04": ["IaC", "Azure resource configuration", "platform profile baseline"], "05": ["source tree", "tests", "CI workflows"],
    "06": ["orchestrator source", "prompts"], "07": ["source", "IaC"], "08": ["source", "tests"], "09": ["tests", "CI workflows", "docs"],
    "10": ["IaC", "source", "Azure RBAC not collected"], "11": ["source", "IaC"], "12": ["CI workflows", "Git history"],
}
for c in a["criteria"]:
    if c["id"] in DETAIL:
        c.update(DETAIL[c["id"]])
    elif c["id"] in NA:
        c.update(applicability="not_applicable", applicability_justification=NA[c["id"]], status="not_applicable",
                 maturity="N/A", confidence="medium", discovery_coverage="complete", discovery_attempts=["README", "source", "IaC"])
    else:
        c.update(discovery_coverage="attempted", discovery_attempts=[f"searched {s}; no evidence found" for s in DOMAIN_ATTEMPTS[c["domain"]]],
                 unknowns=["No evidence in the inspected sources."])
        if c.get("emphasis") in ("high", "critical") and not c.get("follow_up_questions"):
            c["follow_up_questions"] = [f"Where is '{c['title']}' implemented or documented?"]

a["observations"] = [
    {"id": "OBS-001", "domain": "10", "category": "retain", "nature": "strength",
     "observation": "Keyless authentication end to end.", "existing_implementation": "Managed identity with least-privilege roles; local auth disabled on Foundry.",
     "implication": "Removes key rotation and leakage risk for model access.", "evidence_refs": ["EV-BICEP-MI", "EV-APP-CRED", "EV-AZ-FOUNDRY-1"],
     "criteria": ["PLT-02", "SG-02"], "confidence": "high", "risk_severity": "informational", "validation_status": "unvalidated"},
    {"id": "OBS-002", "domain": "08", "category": "improve", "nature": "potential_gap",
     "observation": "Claim enumeration completeness is not verified.", "existing_implementation": "One model call lists claims; count is not reconciled with the source.",
     "implication": "Unlisted claims are never verified, so a clean report may be incomplete.", "evidence_refs": ["EV-ORCH-ENUM", "EV-BRIEF-CLAIMS"],
     "criteria": ["FA-03", "WRK-01"], "confidence": "medium", "risk_severity": "high",
     "improvement_options": [{"option": "Deterministic pre-extraction of numeric tokens and reconciliation with model-listed claims.",
                              "trade_offs": "Extra parsing code; catches omissions independent of the model."}],
     "follow_up_question": "Is there any measurement of claim-enumeration recall?", "owner": "development team", "validation_status": "unvalidated"},
    {"id": "OBS-003", "domain": "09", "category": "introduce", "nature": "potential_gap",
     "observation": "No evaluation framework.", "existing_implementation": "Only parsing unit tests exist.",
     "implication": "Prompt or model changes cannot be shown to preserve review quality.", "evidence_refs": ["EV-NO-EVALS"],
     "criteria": ["EG-01"], "confidence": "high", "risk_severity": "high",
     "improvement_options": [{"option": "Labelled claim set with stage-level recall and precision in CI.", "trade_offs": "Needs curated ground truth."}],
     "follow_up_question": "Are evaluations run outside this repository?", "validation_status": "unvalidated"},
    {"id": "OBS-004", "domain": "04", "category": "improve", "nature": "potential_gap",
     "observation": "AI Search is publicly reachable.", "existing_implementation": "Private endpoints for Foundry and storage, not for search.",
     "implication": "Deviates from the platform private-networking baseline.", "evidence_refs": ["EV-BICEP-PE", "EV-AZ-SEARCH-1"],
     "criteria": ["PLT-01", "WA-02"], "confidence": "high", "risk_severity": "medium",
     "follow_up_question": "Is the public search endpoint a documented exception?", "validation_status": "unvalidated"},
    {"id": "OBS-005", "domain": "08", "category": "retain", "nature": "strength",
     "observation": "Deterministic numeric comparison.", "existing_implementation": "Decimal arithmetic with explicit tolerance.",
     "implication": "Verification outcome is reproducible once values are extracted.", "evidence_refs": ["EV-ORCH-NUMERIC"],
     "criteria": ["WRK-02"], "confidence": "high", "risk_severity": "informational", "validation_status": "unvalidated"},
]
a["open_questions"] = [
    {"id": "Q-001", "priority": "P1", "audience": "development_team", "question": "How is completeness of claim enumeration measured today?",
     "why_it_matters": "Exhaustive review is the core promise; enumeration is unchecked.", "criteria": ["FA-03", "WRK-01"], "evidence_refs": ["EV-ORCH-ENUM"]},
    {"id": "Q-002", "priority": "P1", "audience": "development_team", "question": "Do evaluation datasets or results exist outside this repository?",
     "why_it_matters": "Determines whether EG-01 is a gap or a scope limitation.", "criteria": ["EG-01"], "evidence_refs": ["EV-NO-EVALS"]},
    {"id": "Q-003", "priority": "P2", "audience": "platform_owner", "question": "Is public access on the search service an approved exception?",
     "why_it_matters": "Decides whether PLT-01 is a deviation or an accepted risk.", "criteria": ["PLT-01"], "evidence_refs": ["EV-AZ-SEARCH-1"]},
    {"id": "Q-004", "priority": "P3", "audience": "business_owner", "question": "What review volume and turnaround are targeted for production?",
     "why_it_matters": "Sizes model capacity and scaling design.", "criteria": ["BC-01"], "evidence_refs": ["EV-INTERVIEW-VOLUME"]},
]
dump("assessment.json", a)

# ---------------------------------------------------------------- architecture
P = lambda d="unknown", i="unknown", dep="unknown", r="unknown": {"declared": d, "implemented": i, "deployed": dep, "runtime": r}
ent = lambda id, t, name, purpose, refs, conf="high", **kw: {"id": id, "type": t, "name": name, "purpose": purpose,
    "environment": kw.pop("environment", "test"), "perspectives": kw.pop("perspectives", P("present", "present", "unknown")),
    "evidence_refs": refs, "confidence": conf, **kw}
dump("architecture.json", {"schema_version": "1.0.0", "entities": [
    ent("ENT-USER", "user_role", "Claims adjuster", "Uploads a claim summary and reads the review.", ["EV-README-PURPOSE"], "medium",
        perspectives=P("present", "unknown", "unknown")),
    ent("ENT-APP", "application", "Review API", "Receives uploads and runs the review pipeline.", ["EV-ORCH-LOOP", "EV-CONFIG-SETTINGS"]),
    ent("ENT-PIPE", "workflow", "Review pipeline", "Extract, verify, summarise.", ["EV-ORCH-LOOP"], parent="ENT-APP"),
    ent("ENT-MI", "identity", "Workload identity", "User-assigned managed identity for the app.", ["EV-BICEP-MI", "EV-APP-CRED"]),
    ent("ENT-FOUNDRY", "azure_resource", "Foundry account", "Hosts model deployments.", ["EV-AZ-FOUNDRY-1", "EV-REQ-SDKS"],
        azure_alias="AZ-FOUNDRY-1", azure_type="Microsoft.CognitiveServices/accounts", perspectives=P("present", "present", "present")),
    ent("ENT-SEARCH", "search_index", "Policy index", "Reference policy lookups during verification.", ["EV-AZ-SEARCH-1", "EV-BICEP-PE"], "medium",
        azure_alias="AZ-SEARCH-1", azure_type="Microsoft.Search/searchServices", perspectives=P("present", "unknown", "present"),
        unknown_properties=["index schema", "chunking", "embedding model"]),
], "relationships": [
    {"id": "REL-USER-APP", "source": "ENT-USER", "target": "ENT-APP", "direction": "source_to_target", "purpose": "Upload and read review",
     "protocol": "HTTPS", "authentication": "unknown", "network_path": "unknown", "mode": "synchronous",
     "perspectives": P("present", "unknown", "unknown"), "evidence_refs": ["EV-README-PURPOSE"], "confidence": "low"},
    {"id": "REL-APP-FOUNDRY", "source": "ENT-APP", "target": "ENT-FOUNDRY", "direction": "source_to_target", "purpose": "Model inference per stage",
     "protocol": "HTTPS", "authentication": "managed_identity_user", "identity": "ENT-MI", "network_path": "private_endpoint", "mode": "synchronous",
     "perspectives": P("present", "present", "present"), "evidence_refs": ["EV-APP-CRED", "EV-BICEP-PE", "EV-AZ-FOUNDRY-1"], "confidence": "high"},
    {"id": "REL-APP-SEARCH", "source": "ENT-APP", "target": "ENT-SEARCH", "direction": "source_to_target", "purpose": "Policy lookup",
     "protocol": "HTTPS", "authentication": "unknown", "network_path": "public_internet", "mode": "synchronous",
     "perspectives": P("present", "unknown", "present"), "evidence_refs": ["EV-AZ-SEARCH-1"], "confidence": "medium"},
]})

dump("execution-flows.json", {"schema_version": "1.0.0", "flows": [{
    "id": "FLOW-REVIEW", "name": "Claim summary review", "trigger": "HTTP upload", "entry_point": "ENT-APP",
    "description": "Code-defined three-stage pipeline; each stage is one model call with a typed output.", "orchestration": "deterministic",
    "evidence_refs": ["EV-ORCH-LOOP"], "confidence": "high", "steps": [
        {"id": "S1", "order": 1, "kind": "trigger", "actor": "ENT-USER", "target": "ENT-APP", "description": "Adjuster uploads a summary.",
         "determinism": "human", "next": ["S2"], "evidence_refs": ["EV-README-PURPOSE"], "confidence": "medium"},
        {"id": "S2", "order": 2, "kind": "model_call", "actor": "ENT-PIPE", "target": "ENT-FOUNDRY", "description": "Enumerate numeric claims.",
         "determinism": "model_driven", "next": ["S3"], "on_failure": "S9", "retry": "3 attempts, exponential backoff",
         "evidence_refs": ["EV-ORCH-ENUM"], "confidence": "high"},
        {"id": "S3", "order": 3, "kind": "loop", "actor": "ENT-PIPE", "description": "For each claim: extract values and compare.",
         "determinism": "deterministic", "loop_bound": "number of enumerated claims", "next": ["S4"], "evidence_refs": ["EV-ORCH-NUMERIC"], "confidence": "high"},
        {"id": "S4", "order": 4, "kind": "model_call", "actor": "ENT-PIPE", "target": "ENT-FOUNDRY", "description": "Summarise discrepancies for the adjuster.",
         "determinism": "model_driven", "next": ["S5"], "on_failure": "S9", "evidence_refs": ["EV-ORCH-LOOP"], "confidence": "high"},
        {"id": "S5", "order": 5, "kind": "output", "actor": "ENT-APP", "target": "ENT-USER", "description": "Return review; no approval step found.",
         "determinism": "deterministic", "next": [], "evidence_refs": ["EV-ORCH-LOOP"], "confidence": "medium"},
        {"id": "S9", "order": 9, "kind": "error_handler", "actor": "ENT-APP", "description": "Return a failed-review status.",
         "determinism": "deterministic", "next": [], "evidence_refs": ["EV-ORCH-LOOP"], "confidence": "medium"},
    ]}]})

dump("technology-inventory.json", {"schema_version": "1.0.0", "items": [
    {"id": "TECH-PROJECTS-SDK", "name": "azure-ai-projects", "category": "sdk", "vendor": "microsoft", "version": "1.0.0",
     "version_source": "requirements.txt", "lifecycle": "ga", "lifecycle_source": "package index", "lifecycle_verified_at": "2025-01-15",
     "usage": "Client for Foundry model calls.", "native_vs_custom": "native", "evidence_refs": ["EV-REQ-SDKS"], "confidence": "high"},
    {"id": "TECH-PIPELINE", "name": "Review pipeline", "category": "bespoke_component", "vendor": "bespoke", "version": None,
     "lifecycle": "not_applicable", "usage": "Code-defined orchestration of three model stages.", "native_vs_custom": "custom",
     "selection_rationale": "Reduce hosting effort (ADR 0002).", "rationale_documented": True,
     "alternatives_to_investigate": [{"capability": "Foundry Agent Service workflows", "lifecycle": "unknown",
                                      "why": "Managed orchestration with built-in tracing.", "trade_offs": "Less control over typed stage outputs."}],
     "evidence_refs": ["EV-ORCH-LOOP", "EV-ADR-FRAMEWORK"], "confidence": "high"},
], "external_verification": [{"topic": "azure-ai-projects lifecycle", "source": "package index release history", "verified_at": "2025-01-15"}]})

dump("workload-characteristics.json", {"schema_version": "1.0.0", "characteristics": [
    {"id": "WL-VOLUME", "name": "Reviews per week", "value": "a few hundred", "unit": "reviews/week", "value_type": "estimate",
     "environment": "production", "source": "team interview", "evidence_refs": ["EV-INTERVIEW-VOLUME"], "confidence": "low"},
    {"id": "WL-CLAIMS", "name": "Claims per document", "value": None, "unit": "claims", "value_type": "unknown",
     "notes": "Not measured; needed as recall denominator.", "evidence_refs": [], "confidence": "none"},
]})

dump("design-decisions.json", {"schema_version": "1.0.0", "decisions": [
    {"id": "DD-001", "title": "Bespoke pipeline over Foundry SDK", "decision": "Code-defined three-stage pipeline calling Foundry models.",
     "status": "documented", "rationale_documented": True, "rationale": "Reduce hosting effort.", "alternatives_considered": ["Bespoke agent loop", "Hosted agent"],
     "preliminary_view": "retain", "evidence_refs": ["EV-ADR-FRAMEWORK", "EV-ORCH-LOOP"], "criteria": ["MT-04", "AE-04"]},
    {"id": "DD-002", "title": "Public AI Search endpoint", "decision": "Search service deployed with public network access.",
     "status": "inferred_from_implementation", "rationale_documented": False, "rationale": None,
     "preliminary_view": "investigate", "evidence_refs": ["EV-AZ-SEARCH-1"], "criteria": ["PLT-01"]},
]})

dump("azure-configuration.json", {"schema_version": "1.0.0",
    "collections": [{"environment": "test", "subscription_alias": "AZ-SUB-1", "resource_group_alias": "AZ-RG-1",
                     "authorised_by": "platform owner", "collected_at": TS, "telemetry": False}],
    "resources": [
        {"alias": "AZ-FOUNDRY-1", "type": "Microsoft.CognitiveServices/accounts", "kind": "AIServices", "location": "westeurope",
         "environment": "test", "resource_group_alias": "AZ-RG-1",
         "properties": {"publicNetworkAccess": "Disabled", "disableLocalAuth": True, "privateEndpointConnections": 1}, "evidence_ids": ["EV-AZ-FOUNDRY-1"]},
        {"alias": "AZ-SEARCH-1", "type": "Microsoft.Search/searchServices", "kind": None, "location": "westeurope",
         "environment": "test", "resource_group_alias": "AZ-RG-1",
         "properties": {"sku": "standard", "publicNetworkAccess": "Enabled", "privateEndpointConnections": 0}, "evidence_ids": ["EV-AZ-SEARCH-1"]},
    ],
    "attempts": [
        {"collector": "inventory", "target": "AZ-RG-1", "command_template": "az resource list --resource-group {resource_group} --subscription {subscription}", "outcome": "ok"},
        {"collector": "rbac", "target": "AZ-RG-1", "command_template": "az role assignment list --resource-group {resource_group}", "outcome": "forbidden",
         "detail": "Reader role cannot list role assignments at this scope."},
    ]})

m = load("manifest.json")
m["repository"].update(name="contoso-claims-review", remote=None, branch="main")
m["discovery_modes"] = ["repository", "azure_configuration"]
m["environments_inspected"] = [{"name": "test", "inspected_via": ["repository", "azure_configuration"]}]
m["azure_scope"].update(authorised=True, authorised_by="platform owner", cli_available=True, authenticated=True,
                        scopes=[{"environment": "test", "subscription_alias": "AZ-SUB-1", "resource_group_alias": "AZ-RG-1"}],
                        failed_attempts=["rbac: forbidden"])
m["evidence_sources_inspected"] = ["source code", "IaC (Bicep)", "dependency manifest", "ADRs", "prompts", "tests", "Azure resource configuration (test)", "team interview"]
m["evidence_sources_unavailable"] = ["Azure RBAC (forbidden)", "telemetry (not authorised)", "production environment (out of scope)"]
m["limitations"] = ["Synthetic example: all names, paths and values are fictional.",
                    "Production not inspected; deployed evidence covers the test environment only.",
                    "Role assignments could not be read."]
dump("manifest.json", m)

# ---------------------------------------------------------------- markdown
(out / "README.md").write_text((SKILL / "templates" / "package-README.md").read_text(encoding="utf-8")
    .replace("{{application alias}}", "Contoso claims reviewer (synthetic)")
    .replace("{{One sentence on what was and was not inspected.}}",
             "Repository and test-environment Azure configuration inspected; production, telemetry and role assignments not inspected."), encoding="utf-8", newline="\n")

REPORT = """# Design assurance discovery report: Contoso claims reviewer (synthetic)

> Synthetic example. Internal discovery output for independent architectural
> review. Every statement cites evidence IDs from `evidence.json`.

## 1. Application overview

Reviews insurance claim summaries for numeric consistency before adjuster
sign-off (EV-README-PURPOSE). Estimated volume: a few hundred reviews per week,
from interview, not measured (EV-INTERVIEW-VOLUME).

## 2. Discovery scope and limitations

| Item | Value |
| --- | --- |
| Profiles | azure-agent, example-platform, example-document-review |
| Discovery modes | repository, azure_configuration (test), interview |
| Environments inspected | test |
| Evidence sources unavailable | role assignments (forbidden), telemetry (not authorised), production |

## 3. Current implementation and maturity

Working pipeline in test. Coverage and maturity are reported separately in
`discovery-coverage.json`; most criteria remain **U** because only the
repository and one environment were inspected.

## 4. Known challenges and outstanding work

No issue tracker or TODO markers documenting outstanding work were found.

## 5. Architecture

### 5.1 Infrastructure architecture

Foundry account (AZ-FOUNDRY-1, private, local auth disabled) and AI Search
(AZ-SEARCH-1, public) in one resource group (EV-AZ-FOUNDRY-1, EV-AZ-SEARCH-1).

### 5.2 Logical application architecture

```mermaid
flowchart LR
  U[Claims adjuster] -->|HTTPS| A[Review API]
  A -->|MI, private endpoint| F[Foundry AZ-FOUNDRY-1]
  A -->|auth unknown, public| S[AI Search AZ-SEARCH-1]
```

### 5.3 Agent architecture and execution

Deterministic three-stage pipeline FLOW-REVIEW: enumerate claims (model),
compare values (Decimal), summarise (model). No human approval step found
(EV-ORCH-LOOP, EV-ORCH-ENUM, EV-ORCH-NUMERIC).

### 5.4 Knowledge and data architecture

Search index used for policy lookups; schema, chunking and embeddings unknown.

### 5.5 Network and identity architecture

User-assigned managed identity; keyless (EV-BICEP-MI, EV-APP-CRED). Search
reachable publicly (EV-AZ-SEARCH-1).

## 6. Findings by discovery domain

### Domain 01: Business context and workload characteristics

Purpose documented (BC-01, maturity 3). Volume estimated only.

### Domain 02: Microsoft technology stack and current capability alignment

Foundry SDK pinned (MT-02, 3); framework choice documented in ADR (MT-04, 3).

### Domain 03: Azure infrastructure and Well-Architected principles

Network isolation conflicting: baseline vs public search (WA-02, 2).

### Domain 04: Customer platform standards

Keyless auth meets baseline (PLT-02, 4); private networking partial (PLT-01, 2).

### Domain 05: Software engineering and application architecture

Typed configuration (SE-03, 3); exact pins without update tooling (SE-04, 3).

### Domain 06: Agent architecture, orchestration and model strategy

Code-defined control flow (AE-01, AE-04, 3).

### Domain 07: Data ingestion, knowledge architecture and retrieval

No ingestion pipeline: KR-02 not applicable. Index design unknown.

### Domain 08: Functional assurance, correctness and human oversight

Enumeration unchecked (FA-03, WRK-01, 1); numeric comparison deterministic (WRK-02, 3).

### Domain 09: Evaluations, guardrails and behavioural assurance

Evaluation framework confirmed absent in this repository (EG-01, 0; EV-NO-EVALS).

### Domain 10: Security, identity and data governance

Least-privilege workload identity (SG-02, 4). RBAC not collected.

### Domain 11: Observability, reliability, scalability and economics

Per-stage GenAI spans, content recording off (OS-02, 3).

### Domain 12: Lifecycle, traceability and operational ownership

Prompt versioned in Git; no evaluation gate (LT-03, 2).

## 7. Existing strengths

- OBS-001 keyless authentication end to end.
- OBS-005 deterministic numeric comparison.

## 8. Potential gaps and implications

- OBS-002 claim enumeration completeness unverified (high).
- OBS-003 no evaluation framework (high).
- OBS-004 public AI Search endpoint (medium).

## 9. Architectural decisions and rationale

DD-001 documented (ADR 0002). DD-002 inferred; rationale not documented.

## 10. Workload and runtime characteristics

WL-VOLUME estimate only; WL-CLAIMS unknown.

## 11. Unknowns and conflicting evidence

WRK-01: briefing claims exhaustive review; implementation does not verify
completeness. Most criteria are U; see `assessment.csv`.

## 12. Questions for the development team

See `open-questions.md`. P1: Q-001 (enumeration recall), Q-002 (evaluations).
"""
(out / "discovery-report.md").write_text(REPORT, encoding="utf-8", newline="\n")

SUMMARY = """# Executive discovery summary: Contoso claims reviewer (synthetic)

> Internal technical summary for the reviewing architect. Not customer-facing.

## What the application does

Checks claim summaries for numeric consistency before adjuster sign-off (EV-README-PURPOSE).

## How it is implemented

Python API; code-defined three-stage pipeline over Foundry models; managed
identity; AI Search for policy lookups (EV-ORCH-LOOP, EV-BICEP-MI).

## Significant strengths

- OBS-001 keyless authentication, local auth disabled.
- OBS-005 deterministic numeric comparison.

## Material potential gaps

- OBS-002 claim enumeration completeness unverified.
- OBS-003 no evaluation framework in the repository.
- OBS-004 AI Search publicly reachable.

## Important unknowns

- Q-002 whether evaluations exist elsewhere.
- Index design, chunking and embeddings.

## Key technical dependencies

- Foundry model deployments, azure-ai-projects SDK, AI Search.

## Suggested focus for the design assurance review

1. Completeness guarantees for claim enumeration (FA-03, WRK-01).
2. Evaluation strategy and recall measurement (EG-01, WRK-03).
3. Network baseline exception for AI Search (PLT-01).

## Coverage at a glance

See `discovery-coverage.json` for per-domain coverage and maturity.
"""
(out / "executive-discovery-summary.md").write_text(SUMMARY, encoding="utf-8", newline="\n")

ada("render", "--out", str(out))
ada("sanitize", "--out", str(out), "--apply", ok=(0, 1))
ada("check", "--out", str(out))
ada("package", "--out", str(out))

if DEST.exists():
    shutil.rmtree(DEST)
for path in out.rglob("*"):
    rel = path.relative_to(out)
    if path.is_dir() or rel.parts[0] in ("_work", "_dist") or rel.name == ".gitignore":
        continue
    target = DEST / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
print("example written to", DEST)
shutil.rmtree(tmp, ignore_errors=True)
