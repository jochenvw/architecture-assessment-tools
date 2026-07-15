"""Command-line interface and orchestration.

Implements the operations exposed by the skill: ``doctor``, ``inventory``,
``scan``, ``resume``, ``status``, ``report``, ``reevaluate`` and ``refresh``.
Orchestration keeps the phase boundary explicit: inventory completes before any
detailed collection, shared peripheral resources are scanned once per snapshot,
and ``reevaluate`` performs no Azure calls.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
import uuid
from pathlib import Path
from typing import Optional

from . import __version__
from .azure_cli import AzureClient, AzureError, build_client
from .collectors import CollectorContext
from .collectors import apim as apim_collector
from .collectors import connections as connections_collector
from .collectors import cosmos as cosmos_collector
from .collectors import foundry as foundry_collector
from .collectors import foundry_projects as projects_collector
from .collectors import keyvault as keyvault_collector
from .collectors import model_deployments as deployments_collector
from .collectors import networking as networking_collector
from .collectors import observability as observability_collector
from .collectors import search as search_collector
from .collectors import storage as storage_collector
from .database import Database
from .evidence import EvidenceStore, utcnow
from .inventory import resolve_subscription_scope, run_inventory
from .models import Scope
from .rules import evaluate as evaluate_rules
from .rules import load_standard
from .effort import estimate_all
from .reporting import generate_reports
from .scheduler import Scheduler, TaskSpec, TaskStatus

FOUNDRY_COLLECTORS = {
    "foundry": foundry_collector.collect,
    "projects": projects_collector.collect,
    "model-deployments": deployments_collector.collect,
    "connections": connections_collector.collect,
    "networking": networking_collector.collect,
    "observability": observability_collector.collect,
}

PERIPHERAL_COLLECTORS = {
    "keyvault": keyvault_collector.collect,
    "cosmos": cosmos_collector.collect,
    "storage": storage_collector.collect,
    "search": search_collector.collect,
    "apim": apim_collector.collect,
}

# Peripheral resource classification -> collector name.
PERIPHERAL_CLASSIFICATION = {
    "keyvault": "keyvault",
    "cosmos": "cosmos",
    "storage": "storage",
    "search": "search",
    "apim": "apim",
}

DEFAULT_STANDARD = Path(__file__).resolve().parents[2] / "standards" / "standard-foundry-v1.yaml"


# ---------------------------------------------------------------------------
# Paths & scope helpers
# ---------------------------------------------------------------------------
def _output_paths(output: Path) -> dict[str, Path]:
    output = Path(output)
    return {
        "root": output,
        "db": output / "assessment.db",
        "raw": output / "raw",
        "logs": output / "logs",
        "reports": output / "reports",
    }


def _resolve_scope(args: argparse.Namespace) -> Scope:
    if getattr(args, "all_accessible", False):
        return Scope("all-accessible")
    if getattr(args, "subscription", None):
        return Scope("subscription", tuple(args.subscription))
    if getattr(args, "resource_id", None):
        return Scope("resource", tuple(args.resource_id))
    if getattr(args, "resource_group", None):
        return Scope("resource-group", tuple(args.resource_group))
    if getattr(args, "management_group", None):
        return Scope("management-group", (args.management_group,))
    return Scope("all-accessible")


def _make_client(args: argparse.Namespace) -> AzureClient:
    fixture = getattr(args, "fixture", None)
    return build_client(Path(fixture) if fixture else None)


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
def _preflight(client: AzureClient, scope: Scope) -> dict:
    info: dict = {"errors": []}
    try:
        account = client.account_show()
        info["tenant_id"] = account.get("tenantId")
        user = account.get("user") or {}
        info["identity"] = user.get("name") or account.get("name")
        info["identity_type"] = user.get("type")
    except AzureError as exc:
        info["errors"].append(f"identity: {exc}")
    try:
        info["cli_version"] = client.cli_version()
    except AzureError as exc:
        info["cli_version"] = "unknown"
        info["errors"].append(f"cli-version: {exc}")
    try:
        accessible, unavailable = resolve_subscription_scope(client, scope)
        info["accessible_subscriptions"] = len(accessible)
        info["unavailable_subscriptions"] = len(unavailable)
    except AzureError as exc:
        info["errors"].append(f"subscriptions: {exc}")
        info["accessible_subscriptions"] = 0
    return info


# ---------------------------------------------------------------------------
# Run/snapshot bootstrap
# ---------------------------------------------------------------------------
def _ensure_run(db: Database, args: argparse.Namespace, scope: Scope, preflight: dict, standard) -> str:
    existing = db.latest_run()
    assessment_id = existing["assessment_id"] if existing else str(uuid.uuid4())
    db.upsert_run(
        {
            "assessment_id": assessment_id,
            "scope_kind": scope.kind,
            "scope_values": ",".join(scope.values),
            "tenant_id": preflight.get("tenant_id"),
            "identity": preflight.get("identity"),
            "identity_type": preflight.get("identity_type"),
            "cli_version": preflight.get("cli_version"),
            "scanner_version": __version__,
            "standard_id": standard.id,
            "standard_version": standard.version,
            "started_at": existing["started_at"] if existing else utcnow(),
            "updated_at": utcnow(),
            "concurrency": getattr(args, "concurrency", 4),
            "output_dir": str(args.output),
            "no_raw_evidence": 1 if getattr(args, "no_raw_evidence", False) else 0,
        }
    )
    return assessment_id


def _build_context(db: Database, client: AzureClient, snapshot_id: str, paths: dict, no_raw: bool) -> CollectorContext:
    store = EvidenceStore(paths["raw"], no_raw_evidence=no_raw)
    return CollectorContext(db=db, client=client, snapshot_id=snapshot_id, evidence=store)


def _foundry_task_specs(db: Database, snapshot_id: str) -> list[TaskSpec]:
    specs = []
    foundries = db.list_resources(
        snapshot_id,
        classifications=["foundry-current", "foundry-classic-hub", "azure-openai-account",
                         "ai-services-account", "unknown-cognitive-account"],
    )
    for f in foundries:
        for collector in FOUNDRY_COLLECTORS:
            specs.append(TaskSpec(resource_id=f["resource_id"], collector=collector))
    return specs


def _peripheral_task_specs(db: Database, snapshot_id: str) -> list[TaskSpec]:
    specs = []
    for classification, collector in PERIPHERAL_CLASSIFICATION.items():
        for res in db.list_resources(snapshot_id, classifications=[classification]):
            specs.append(TaskSpec(resource_id=res["resource_id"], collector=collector))
    return specs


def _register_central_apim(db: Database, ctx: CollectorContext, snapshot_id: str, standard) -> None:
    from .collectors import parse_resource_group, parse_subscription

    for apim_id in standard.parameters.get("central_apim_resource_ids", []) or []:
        ctx.register_resource(
            {
                "resource_id": apim_id,
                "subscription_id": parse_subscription(apim_id),
                "resource_group": parse_resource_group(apim_id),
                "name": apim_id.rstrip("/").split("/")[-1],
                "resource_type": "microsoft.apimanagement/service",
                "kind": None, "sku": None, "location": None,
                "tags": {}, "classification": "apim", "properties": {},
            }
        )


def _run_scheduler(db, assessment_id, snapshot_id, specs, executors_map, ctx, args) -> "Scheduler":
    scheduler = Scheduler(
        db=db,
        assessment_id=assessment_id,
        snapshot_id=snapshot_id,
        concurrency=getattr(args, "concurrency", 4),
        retry_blocked=getattr(args, "retry_blocked", False),
        refresh=getattr(args, "_refresh_tasks", False),
    )
    executors = {name: (lambda rid, fn=fn: fn(ctx, rid)) for name, fn in executors_map.items()}

    def handle_sigint(_signum, _frame):
        scheduler.request_stop()

    previous = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, handle_sigint)
    try:
        scheduler.run(specs, executors)
    finally:
        signal.signal(signal.SIGINT, previous)
    return scheduler


def _evaluate_and_report(db: Database, assessment_id: str, snapshot_id: str, standard, paths: dict, scope: Scope) -> dict:
    db.clear_findings(assessment_id, snapshot_id)
    for finding in evaluate_rules(db, snapshot_id, standard):
        db.insert_finding(assessment_id, snapshot_id, {
            "resource_id": finding.resource_id,
            "rule_id": finding.rule_id,
            "rule_version": finding.rule_version,
            "result": finding.result,
            "effective_result": finding.effective_result,
            "severity": finding.severity,
            "expected": finding.expected,
            "actual": finding.actual,
            "explanation": finding.explanation,
            "recommended_investigation": finding.recommended_investigation,
            "collection_status": finding.collection_status,
            "foundry_resource_id": finding.foundry_resource_id,
            "project_resource_id": finding.project_resource_id,
            "evidence_ref": finding.evidence_ref,
            "exception_id": finding.exception_id,
            "evaluated_at": utcnow(),
        })
    db.clear_effort(assessment_id, snapshot_id)
    for estimate in estimate_all(db, snapshot_id, standard.effort):
        db.insert_effort(assessment_id, snapshot_id, estimate)
    return generate_reports(
        db, assessment_id, snapshot_id, paths["reports"],
        standard.id, standard.version, __version__, scope.label(),
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_doctor(args: argparse.Namespace) -> int:
    scope = _resolve_scope(args)
    client = _make_client(args)
    info = _preflight(client, scope)
    if getattr(args, "json", False):
        print(json.dumps(info, indent=2, sort_keys=True))
        return 0 if not info["errors"] else 1
    print("Foundry estate assessment — doctor")
    print(f"  Scanner version:        {__version__}")
    print(f"  Azure CLI version:      {info.get('cli_version', 'unknown')}")
    print(f"  Tenant:                 {info.get('tenant_id', 'unknown')}")
    print(f"  Identity:               {info.get('identity', 'unknown')} ({info.get('identity_type', 'unknown')})")
    print(f"  Requested scope:        {scope.label()}")
    print(f"  Accessible subs:        {info.get('accessible_subscriptions', 0)}")
    print(f"  Unavailable subs:       {info.get('unavailable_subscriptions', 0)}")
    if info["errors"]:
        print("  Issues:")
        for err in info["errors"]:
            print(f"    - {err}")
        print("  Ensure you have run 'az login' and have Reader access to target subscriptions.")
        return 1
    print("  Preflight OK.")
    return 0


def _open_db(args: argparse.Namespace) -> tuple[Database, dict]:
    paths = _output_paths(Path(args.output))
    for key in ("root", "raw", "logs", "reports"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return Database(paths["db"]), paths


def cmd_inventory(args: argparse.Namespace) -> int:
    scope = _resolve_scope(args)
    standard = load_standard(Path(args.standard))
    client = _make_client(args)
    db, paths = _open_db(args)
    preflight = _preflight(client, scope)
    assessment_id = _ensure_run(db, args, scope, preflight, standard)
    snapshot_id = run_inventory(db, client, assessment_id, scope)
    snap = db.latest_snapshot(assessment_id)
    print(f"Inventory snapshot {snapshot_id} created.")
    print(f"  Subscriptions accessible: {snap['subscriptions_accessible']}")
    print(f"  Candidate Foundry accounts: {snap['candidate_foundries']}")
    db.close()
    return 0


def cmd_scan(args: argparse.Namespace, *, new_snapshot: bool = True) -> int:
    standard = load_standard(Path(args.standard))
    client = _make_client(args)
    db, paths = _open_db(args)
    # Scope is immutable for the life of an assessment: ``_ensure_run`` never
    # overwrites the persisted scope. So on resume/refresh (any run that already
    # exists) reuse the stored scope rather than re-deriving it from argv, which
    # would otherwise silently fall back to ``all-accessible`` and mislabel the
    # regenerated reports. Only a brand-new run derives scope from the flags.
    existing = db.latest_run()
    if existing is not None:
        scope = Scope(existing["scope_kind"], tuple(v for v in existing["scope_values"].split(",") if v))
    else:
        scope = _resolve_scope(args)
    preflight = _preflight(client, scope)
    assessment_id = _ensure_run(db, args, scope, preflight, standard)

    snap = db.latest_snapshot(assessment_id)
    if new_snapshot or snap is None:
        snapshot_id = run_inventory(db, client, assessment_id, scope)
    else:
        snapshot_id = snap["snapshot_id"]
    snap = db.latest_snapshot(assessment_id)
    print(f"Scope: {scope.label()} | snapshot {snapshot_id} | candidates {snap['candidate_foundries']}")

    ctx = _build_context(db, client, snapshot_id, paths, getattr(args, "no_raw_evidence", False))
    _register_central_apim(db, ctx, snapshot_id, standard)

    # Phase 2/3: Foundry enrichment + relationship discovery.
    foundry_specs = _foundry_task_specs(db, snapshot_id)
    scheduler = _run_scheduler(db, assessment_id, snapshot_id, foundry_specs, FOUNDRY_COLLECTORS, ctx, args)

    interrupted = scheduler._stop.is_set()
    if not interrupted:
        # Phase 4: peripheral profiling (unique resources scanned once).
        peripheral_specs = _peripheral_task_specs(db, snapshot_id)
        scheduler = _run_scheduler(db, assessment_id, snapshot_id, peripheral_specs, PERIPHERAL_COLLECTORS, ctx, args)
        interrupted = scheduler._stop.is_set()

    if interrupted:
        print("\nInterrupted. State saved. Resume with:")
        print(f"  python scripts/foundry_estate_assessment.py resume --output {args.output}")
        db.close()
        return 130

    reports = _evaluate_and_report(db, assessment_id, snapshot_id, standard, paths, scope)
    print(f"Assessment complete. Reports written to: {reports['reports_dir']}")
    db.close()
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    return cmd_scan(args, new_snapshot=False)


def cmd_refresh(args: argparse.Namespace) -> int:
    return cmd_scan(args, new_snapshot=True)


def cmd_status(args: argparse.Namespace) -> int:
    db, paths = _open_db(args)
    run = db.latest_run()
    if run is None:
        print("No assessment found at this output directory.")
        db.close()
        return 1
    snap = db.latest_snapshot(run["assessment_id"])
    if snap is None:
        print("Assessment exists but no inventory snapshot yet. Run 'scan' or 'inventory'.")
        db.close()
        return 0
    tasks = db.list_tasks(run["assessment_id"], snap["snapshot_id"])
    from collections import Counter

    status_counts = Counter(t["status"] for t in tasks)
    collector_counts: dict[str, Counter] = {}
    for t in tasks:
        collector_counts.setdefault(t["collector"], Counter())[t["status"]] += 1

    payload = {
        "assessment": run["started_at"],
        "scope": Scope(run["scope_kind"], tuple(v for v in run["scope_values"].split(",") if v)).label(),
        "standard": f"{run['standard_id']} {run['standard_version']}",
        "inventory": {
            "subscriptions": snap["subscriptions_accessible"],
            "foundries": snap["candidate_foundries"],
        },
        "tasks": dict(status_counts),
        "collectors": {name: dict(counts) for name, counts in sorted(collector_counts.items())},
    }
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
        db.close()
        return 0

    print(f"Assessment: {run['started_at']}")
    print(f"Scope: {payload['scope']}")
    print(f"Standard: {payload['standard']}")
    print("")
    print("Inventory")
    print(f"  Subscriptions: {snap['subscriptions_accessible']}")
    print(f"  Foundries discovered: {snap['candidate_foundries']}")
    print("")
    print("Detailed assessment")
    for status in sorted(status_counts):
        print(f"  {status}: {status_counts[status]}")
    print("")
    print("Collectors")
    for name, counts in sorted(collector_counts.items()):
        done = counts.get("SUCCEEDED", 0) + counts.get("PARTIAL", 0)
        total = sum(counts.values())
        print(f"  {name}: {done}/{total}")
    remaining = status_counts.get("PENDING", 0) + status_counts.get("RETRYABLE_ERROR", 0) + status_counts.get("RUNNING", 0)
    print("")
    if remaining:
        print("Next action:")
        print(f"  python scripts/foundry_estate_assessment.py resume --output {args.output}")
    else:
        print("Next action:")
        print(f"  python scripts/foundry_estate_assessment.py report --output {args.output}")
    db.close()
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    standard = load_standard(Path(args.standard))
    db, paths = _open_db(args)
    run = db.latest_run()
    if run is None:
        print("No assessment found. Run 'scan' first.")
        db.close()
        return 1
    snap = db.latest_snapshot(run["assessment_id"])
    if snap is None:
        print("No inventory snapshot. Run 'scan' first.")
        db.close()
        return 1
    scope = Scope(run["scope_kind"], tuple(v for v in run["scope_values"].split(",") if v))
    # If findings are absent, evaluate (no Azure calls) before reporting.
    if not db.list_findings(run["assessment_id"], snap["snapshot_id"]):
        _evaluate_and_report(db, run["assessment_id"], snap["snapshot_id"], standard, paths, scope)
    else:
        generate_reports(db, run["assessment_id"], snap["snapshot_id"], paths["reports"],
                          run["standard_id"], run["standard_version"], __version__, scope.label())
    print(f"Reports written to: {paths['reports']}")
    db.close()
    return 0


def cmd_reevaluate(args: argparse.Namespace) -> int:
    """Re-run rules and effort against a (possibly changed) standard. No Azure."""
    standard = load_standard(Path(args.standard))
    db, paths = _open_db(args)
    run = db.latest_run()
    if run is None:
        print("No assessment found. Run 'scan' first.")
        db.close()
        return 1
    snap = db.latest_snapshot(run["assessment_id"])
    if snap is None:
        print("No inventory snapshot found.")
        db.close()
        return 1
    scope = Scope(run["scope_kind"], tuple(v for v in run["scope_values"].split(",") if v))
    db.upsert_run({**dict(run), "standard_id": standard.id, "standard_version": standard.version, "updated_at": utcnow()})
    reports = _evaluate_and_report(db, run["assessment_id"], snap["snapshot_id"], standard, paths, scope)
    print(f"Re-evaluated against {standard.id} {standard.version}. Reports: {reports['reports_dir']}")
    db.close()
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def _add_scope_flags(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--all-accessible", action="store_true", help="All subscriptions accessible to the current identity.")
    group.add_argument("--subscription", nargs="+", metavar="SUB_ID", help="One or more subscription IDs.")
    group.add_argument("--resource-id", nargs="+", metavar="RESOURCE_ID", help="One or more Foundry resource IDs.")
    group.add_argument("--resource-group", nargs="+", metavar="RG_ID", help="One or more resource-group resource IDs.")
    group.add_argument("--management-group", metavar="MG_ID", help="A management group (where permitted).")


def _add_common(parser: argparse.ArgumentParser, *, scope: bool = True) -> None:
    parser.add_argument("--output", required=True, help="Output directory for state and reports.")
    parser.add_argument("--standard", default=str(DEFAULT_STANDARD), help="Path to the standard YAML file.")
    parser.add_argument("--fixture", help="Run against an offline fixture directory instead of Azure.")
    if scope:
        _add_scope_flags(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="foundry_estate_assessment",
        description="Deterministic, resumable Azure AI Foundry estate assessment scanner.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser("doctor", help="Run preflight checks.")
    _add_common(p_doctor)
    p_doctor.add_argument("--json", action="store_true")
    p_doctor.set_defaults(func=cmd_doctor, output=".")
    # doctor should not strictly require --output; relax it.
    for action in p_doctor._actions:
        if getattr(action, "dest", None) == "output":
            action.required = False

    p_inv = sub.add_parser("inventory", help="Build a stable inventory snapshot only.")
    _add_common(p_inv)
    p_inv.set_defaults(func=cmd_inventory)

    p_scan = sub.add_parser("scan", help="Inventory then collect, evaluate and report.")
    _add_common(p_scan)
    p_scan.add_argument("--concurrency", type=int, default=4)
    p_scan.add_argument("--no-raw-evidence", action="store_true")
    p_scan.add_argument("--retry-blocked", action="store_true")
    p_scan.set_defaults(func=cmd_scan)

    p_resume = sub.add_parser("resume", help="Resume an interrupted scan (no re-inventory).")
    _add_common(p_resume)
    p_resume.add_argument("--concurrency", type=int, default=4)
    p_resume.add_argument("--no-raw-evidence", action="store_true")
    p_resume.add_argument("--retry-blocked", action="store_true")
    p_resume.set_defaults(func=cmd_resume)

    p_refresh = sub.add_parser("refresh", help="Take a new inventory snapshot and rescan.")
    _add_common(p_refresh)
    p_refresh.add_argument("--concurrency", type=int, default=4)
    p_refresh.add_argument("--no-raw-evidence", action="store_true")
    p_refresh.add_argument("--retry-blocked", action="store_true")
    p_refresh.set_defaults(func=cmd_refresh)

    p_status = sub.add_parser("status", help="Show progress for an assessment.")
    p_status.add_argument("--output", required=True)
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_report = sub.add_parser("report", help="Generate reports from collected evidence.")
    p_report.add_argument("--output", required=True)
    p_report.add_argument("--standard", default=str(DEFAULT_STANDARD))
    p_report.set_defaults(func=cmd_report)

    p_reeval = sub.add_parser("reevaluate", help="Re-run rules against a standard (no Azure calls).")
    p_reeval.add_argument("--output", required=True)
    p_reeval.add_argument("--standard", default=str(DEFAULT_STANDARD))
    p_reeval.set_defaults(func=cmd_reevaluate)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
