"""Reports are deterministic and reevaluation uses only stored evidence."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _harness import Pipeline
from foundry_estate_assessment import __version__
from foundry_estate_assessment.effort import estimate_all
from foundry_estate_assessment.reporting import generate_reports
from foundry_estate_assessment.rules import evaluate as evaluate_rules

_DETERMINISTIC_FILES = ["findings.csv", "foundries.csv", "relationships.csv",
                        "migration-effort.csv", "unknowns.csv"]


def _persist_findings_and_effort(pipe):
    pipe.db.clear_findings(pipe.assessment_id, pipe.snapshot_id)
    for f in evaluate_rules(pipe.db, pipe.snapshot_id, pipe.standard):
        pipe.db.insert_finding(pipe.assessment_id, pipe.snapshot_id, {
            "resource_id": f.resource_id, "rule_id": f.rule_id, "rule_version": f.rule_version,
            "result": f.result, "effective_result": f.effective_result, "severity": f.severity,
            "expected": f.expected, "actual": f.actual, "explanation": f.explanation,
            "recommended_investigation": f.recommended_investigation,
            "collection_status": f.collection_status, "foundry_resource_id": f.foundry_resource_id,
            "project_resource_id": f.project_resource_id, "evidence_ref": f.evidence_ref,
            "exception_id": f.exception_id, "evaluated_at": "2026-01-01T00:00:00Z",
        })
    pipe.db.clear_effort(pipe.assessment_id, pipe.snapshot_id)
    for e in estimate_all(pipe.db, pipe.snapshot_id, pipe.standard.effort):
        pipe.db.insert_effort(pipe.assessment_id, pipe.snapshot_id, e)


class ReportsTest(unittest.TestCase):
    def test_reports_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                _persist_findings_and_effort(pipe)
                out_a = Path(tmp) / "r1"
                out_b = Path(tmp) / "r2"
                args = (pipe.db, pipe.assessment_id, pipe.snapshot_id)
                generate_reports(*args, out_a, "standard-foundry-v1", "1.0.0", __version__, "all-accessible")
                generate_reports(*args, out_b, "standard-foundry-v1", "1.0.0", __version__, "all-accessible")
                for name in _DETERMINISTIC_FILES:
                    self.assertEqual(
                        (out_a / name).read_text(encoding="utf-8"),
                        (out_b / name).read_text(encoding="utf-8"),
                        f"{name} differs between identical runs",
                    )
            finally:
                pipe.close()

    def test_reevaluate_uses_only_stored_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                first = {(f.foundry_resource_id, f.rule_id): f.result for f in pipe.evaluate()}
                # Discard the Azure client entirely; reevaluation must still work
                # purely from persisted evidence (proving it makes no calls).
                pipe.client = None
                second = {(f.foundry_resource_id, f.rule_id): f.result for f in pipe.evaluate()}
                self.assertEqual(first, second)
            finally:
                pipe.close()


if __name__ == "__main__":
    unittest.main()
