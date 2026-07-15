"""Rule engine behaviour: UNKNOWN is never FAIL; the standard is data-driven."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _harness import Pipeline
from foundry_estate_assessment.rules import evaluate as evaluate_rules

TEAM_A = "team-a-foundry"


def _by_rule(findings, foundry_suffix):
    return {
        f.rule_id: f
        for f in findings
        if (f.foundry_resource_id or "").endswith(foundry_suffix)
    }


class RulesTest(unittest.TestCase):
    def test_missing_evidence_is_unknown_never_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp))
            try:
                # Inventory only: NO collection at all, so all evidence is
                # missing. Every applicable rule must be UNKNOWN or NA, never
                # FAIL.
                pipe.inventory()
                findings = evaluate_rules(pipe.db, pipe.snapshot_id, pipe.standard)
                results = {f.result for f in findings}
                self.assertNotIn("FAIL", results)
                self.assertIn("UNKNOWN", results)
            finally:
                pipe.close()

    def test_compliant_estate_has_no_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                findings = pipe.evaluate()
                team_a = _by_rule(findings, TEAM_A)
                fails = [rid for rid, f in team_a.items() if f.result == "FAIL"]
                self.assertEqual(fails, [], f"unexpected FAIL findings: {fails}")
                # And it did assess real rules (not all NA/UNKNOWN).
                self.assertTrue(any(f.result == "PASS" for f in team_a.values()))
            finally:
                pipe.close()

    def test_standard_change_flips_result_without_code_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                before = _by_rule(pipe.evaluate(), TEAM_A)
                self.assertEqual(before["FND-ACCOUNT-002"].result, "PASS")
                # Change only a parameter; the SKU rule must now FAIL.
                pipe.standard.parameters["expected_foundry_sku"] = "P0"
                after = _by_rule(pipe.evaluate(), TEAM_A)
                self.assertEqual(after["FND-ACCOUNT-002"].result, "FAIL")
            finally:
                pipe.close()

    def test_classic_hub_rules_are_not_applicable(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                team_b = _by_rule(pipe.evaluate(), "team-b-foundry")
                # foundry-current rules do not apply to a classic hub.
                self.assertEqual(team_b["FND-ACCOUNT-001"].result, "NOT_APPLICABLE")
            finally:
                pipe.close()


if __name__ == "__main__":
    unittest.main()
