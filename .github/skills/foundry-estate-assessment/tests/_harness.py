"""Shared test harness: offline pipeline execution against fixtures.

All tests run fully offline. The harness wires the real scanner components
(inventory, collectors, scheduler, rules, effort, reporting) to the
``FixtureCommandRunner`` so no Azure access ever occurs.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# Make the scanner package importable without installation.
_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from foundry_estate_assessment import cli  # noqa: E402
from foundry_estate_assessment.azure_cli import AzureClient, build_client  # noqa: E402
from foundry_estate_assessment.collectors import CollectorContext  # noqa: E402
from foundry_estate_assessment.database import Database  # noqa: E402
from foundry_estate_assessment.evidence import EvidenceStore  # noqa: E402
from foundry_estate_assessment.inventory import run_inventory  # noqa: E402
from foundry_estate_assessment.models import Scope  # noqa: E402
from foundry_estate_assessment.rules import load_standard  # noqa: E402
from foundry_estate_assessment.scheduler import Scheduler  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
COMPLIANT = FIXTURES / "compliant-estate"
DEFAULT_STANDARD = Path(__file__).resolve().parents[1] / "standards" / "standard-foundry-v1.yaml"


def make_client(fixture_dir: Path = COMPLIANT) -> AzureClient:
    return build_client(fixture_dir)


class Pipeline:
    """Runs the full offline pipeline and exposes the resulting state."""

    def __init__(self, output_dir: Path, fixture_dir: Path = COMPLIANT, standard_path: Path = DEFAULT_STANDARD):
        self.output = Path(output_dir)
        self.fixture_dir = Path(fixture_dir)
        self.standard = load_standard(standard_path)
        self.db = Database(self.output / "assessment.db")
        self.client = make_client(fixture_dir)
        self.assessment_id = str(uuid.uuid4())
        self.snapshot_id: str | None = None

    def inventory(self, scope: Scope | None = None) -> str:
        scope = scope or Scope("all-accessible")
        self.snapshot_id = run_inventory(self.db, self.client, self.assessment_id, scope)
        return self.snapshot_id

    def _context(self, no_raw: bool = False) -> CollectorContext:
        store = EvidenceStore(self.output / "raw", no_raw_evidence=no_raw)
        return CollectorContext(db=self.db, client=self.client, snapshot_id=self.snapshot_id, evidence=store)

    def collect(self, no_raw: bool = False) -> None:
        ctx = self._context(no_raw=no_raw)
        cli._register_central_apim(self.db, ctx, self.snapshot_id, self.standard)
        foundry_specs = cli._foundry_task_specs(self.db, self.snapshot_id)
        self._run(foundry_specs, cli.FOUNDRY_COLLECTORS, ctx)
        peripheral_specs = cli._peripheral_task_specs(self.db, self.snapshot_id)
        self._run(peripheral_specs, cli.PERIPHERAL_COLLECTORS, ctx)

    def _run(self, specs, collectors, ctx, concurrency: int = 4) -> Scheduler:
        scheduler = Scheduler(self.db, self.assessment_id, self.snapshot_id, concurrency=concurrency)
        executors = {name: (lambda rid, fn=fn: fn(ctx, rid)) for name, fn in collectors.items()}
        scheduler.run(specs, executors)
        return scheduler

    def evaluate(self):
        from foundry_estate_assessment.rules import evaluate as evaluate_rules

        return list(evaluate_rules(self.db, self.snapshot_id, self.standard))

    def effort(self):
        from foundry_estate_assessment.effort import estimate_all

        return estimate_all(self.db, self.snapshot_id, self.standard.effort)

    def run_all(self) -> "Pipeline":
        self.inventory()
        self.collect()
        return self

    def close(self) -> None:
        self.db.close()
