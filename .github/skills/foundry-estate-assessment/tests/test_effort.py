"""Effort sizing: region dedup, band thresholds, drivers not from rule fails."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _harness import Pipeline
from foundry_estate_assessment.collectors.cosmos import aggregate_regional_metric
from foundry_estate_assessment.effort import _band, _cfg
from foundry_estate_assessment.models import EffortBand


class EffortTest(unittest.TestCase):
    def test_cosmos_region_metric_not_double_counted(self):
        # Two replicated regions holding the same 42.5 GB must aggregate to
        # 42.5 GB (max), not 85 GB (sum).
        samples = [{"region": "a", "value": 42.5}, {"region": "b", "value": 42.5}]
        self.assertEqual(aggregate_regional_metric(samples), 42.5)
        self.assertEqual(aggregate_regional_metric([]), 0.0)

    def test_band_thresholds(self):
        cfg = _cfg({})["bands"]
        self.assertEqual(_band(5, cfg), EffortBand.S)
        self.assertEqual(_band(10, cfg), EffortBand.S)
        self.assertEqual(_band(11, cfg), EffortBand.M)
        self.assertEqual(_band(30, cfg), EffortBand.M)
        self.assertEqual(_band(45, cfg), EffortBand.L)
        self.assertEqual(_band(100, cfg), EffortBand.XL)

    def test_effort_is_independent_of_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipe = Pipeline(Path(tmp)).run_all()
            try:
                estimates = {e["foundry_resource_id"]: e for e in pipe.effort()}
                team_a = next(v for k, v in estimates.items() if k.endswith("team-a-foundry"))
                # Cosmos (48.5) + storage (210) + search (320) footprint drives a
                # large band, and drivers describe *why* (never "N rules failed").
                self.assertIn(team_a["band"], ("L", "XL"))
                self.assertTrue(team_a["drivers"])
                self.assertFalse(any("rule" in d.lower() and "fail" in d.lower() for d in team_a["drivers"]))
                # Shared search dependency must be recognised.
                self.assertTrue(any("shared" in d.lower() for d in team_a["drivers"]))
            finally:
                pipe.close()

    def test_weights_are_configurable(self):
        cfg = _cfg({"weights": {"classic_hub": 999}})
        self.assertEqual(cfg["weights"]["classic_hub"], 999)
        # Untouched weights keep their defaults.
        self.assertEqual(cfg["weights"]["per_project"], 4)


if __name__ == "__main__":
    unittest.main()
