"""Inventory is stable and idempotent for a fixed resource set."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _harness import COMPLIANT, Pipeline
from foundry_estate_assessment.inventory import classify, run_inventory
from foundry_estate_assessment.models import Scope


class InventoryTest(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(classify("AIServices", {"allowProjectManagement": True}), "foundry-current")
        self.assertEqual(classify("AIServices", {"associatedWorkspaces": ["x"]}), "foundry-classic-hub")
        self.assertEqual(classify("AIServices", {}), "ai-services-account")
        self.assertEqual(classify("OpenAI", {}), "azure-openai-account")
        self.assertEqual(classify("Weird", {}), "unknown-cognitive-account")

    def test_inventory_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp))
            try:
                snap_a = pipe.inventory()
                # A second inventory pass over the same fixture yields the same
                # resource set (stable denominator).
                snap_b = run_inventory(pipe.db, pipe.client, pipe.assessment_id, Scope("all-accessible"))
                res_a = {r["resource_id"] for r in pipe.db.list_resources(snap_a)}
                res_b = {r["resource_id"] for r in pipe.db.list_resources(snap_b)}
                self.assertEqual(res_a, res_b)
                # Two candidate Foundries in the fixture.
                snap = pipe.db.latest_snapshot(pipe.assessment_id)
                self.assertEqual(snap["candidate_foundries"], 2)
            finally:
                pipe.close()

    def test_apim_discovered_but_not_a_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp))
            try:
                snap = pipe.inventory()
                apims = pipe.db.list_resources(snap, classifications=["apim"])
                self.assertEqual(len(apims), 1)
                self.assertTrue(apims[0]["resource_id"].endswith("central-apim"))
            finally:
                pipe.close()


if __name__ == "__main__":
    unittest.main()
