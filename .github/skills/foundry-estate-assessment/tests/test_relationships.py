"""Relationships: shared peripherals are scanned once and fan-in is recorded."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _harness import Pipeline


class RelationshipTest(unittest.TestCase):
    def test_shared_search_scanned_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                tasks = pipe.db.list_tasks(pipe.assessment_id, pipe.snapshot_id)
                search_tasks = [t for t in tasks if t["collector"] == "search"]
                # team-a and team-b both connect to the same search service, but
                # it must be profiled exactly once.
                self.assertEqual(len(search_tasks), 1)

                evidence = {e["resource_id"]: e for e in pipe.db.list_evidence(pipe.snapshot_id)
                            if e["collector"] == "search"}
                self.assertEqual(len(evidence), 1)
                (search_ev,) = evidence.values()
                # Fan-in of 2 referencing Foundries is recorded.
                self.assertEqual(search_ev["fact"]["referencingResourceCount"], 2)
            finally:
                pipe.close()

    def test_apim_exposure_relationship_is_directed_from_foundry(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                rels = pipe.db.list_relationships(pipe.snapshot_id)
                exposed = [r for r in rels if r["relationship_type"] == "FOUNDRY_EXPOSED_THROUGH_APIM"]
                self.assertTrue(exposed)
                for r in exposed:
                    # Source is the team Foundry, target is the gateway.
                    self.assertIn("CognitiveServices/accounts", r["source_id"])
                    self.assertIn("ApiManagement/service", r["target_id"])
            finally:
                pipe.close()

    def test_project_relationships_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                types = {r["relationship_type"] for r in pipe.db.list_relationships(pipe.snapshot_id)}
                for expected in ("FOUNDRY_HAS_PROJECT", "PROJECT_USES_COSMOS", "PROJECT_USES_SEARCH"):
                    self.assertIn(expected, types)
            finally:
                pipe.close()


if __name__ == "__main__":
    unittest.main()
