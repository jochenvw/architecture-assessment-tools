"""Regression test for GH issue #4: resume/refresh must preserve the persisted
scope instead of silently falling back to ``all-accessible`` and mislabeling
the regenerated reports.
"""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

import _harness  # noqa: F401  (path bootstrap)
from _harness import COMPLIANT, DEFAULT_STANDARD

from foundry_estate_assessment import cli
from foundry_estate_assessment.database import Database

FIXTURE_SUB = "11111111-1111-1111-1111-111111111111"


def _args(output: Path, *, subscription=None) -> argparse.Namespace:
    return argparse.Namespace(
        output=str(output),
        standard=str(DEFAULT_STANDARD),
        fixture=str(COMPLIANT),
        concurrency=4,
        no_raw_evidence=True,
        retry_blocked=False,
        all_accessible=False,
        subscription=subscription,
        resource_id=None,
        resource_group=None,
        management_group=None,
        json=False,
    )


class ScopePersistenceTest(unittest.TestCase):
    def test_resume_preserves_subscription_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)

            # 1. Scan scoped to a single subscription.
            self.assertEqual(cli.cmd_scan(_args(out, subscription=[FIXTURE_SUB])), 0)

            db = Database(out / "assessment.db")
            self.assertEqual(db.latest_run()["scope_kind"], "subscription")
            db.close()

            # 2. Resume WITHOUT repeating --subscription (subscription=None,
            #    which would otherwise resolve to all-accessible).
            self.assertEqual(cli.cmd_resume(_args(out, subscription=None)), 0)

            # DB scope must be unchanged...
            db = Database(out / "assessment.db")
            run = db.latest_run()
            self.assertEqual(run["scope_kind"], "subscription")
            self.assertEqual(run["scope_values"], FIXTURE_SUB)
            db.close()

            # ...and the regenerated report must not mislabel it as all-accessible.
            summary = (out / "reports" / "executive-summary.md").read_text(encoding="utf-8")
            self.assertIn(FIXTURE_SUB, summary)
            self.assertNotIn("Scope: `all-accessible`", summary)


if __name__ == "__main__":
    unittest.main()
