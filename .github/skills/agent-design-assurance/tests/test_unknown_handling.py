"""Unknown handling and scoring rules: missing information is U, never 0."""

from __future__ import annotations

import unittest

from _harness import TempDirTest, codes, edit_criterion


class UnknownHandlingTest(TempDirTest):
    def setUp(self):
        super().setUp()
        self.out = self.copy_example()

    def test_unknown_status_cannot_be_scored_zero(self):
        edit_criterion(self.out, "EG-02", status="unknown", maturity="0", confidence="low")
        found = codes(self.out)
        self.assertIn("unknown-scored", found)
        self.assertIn("zero-without-absence", found)

    def test_zero_requires_confirmed_absence(self):
        edit_criterion(self.out, "EG-01", absence_confirmed=False)
        self.assertIn("zero-without-absence", codes(self.out))

    def test_absence_needs_supporting_evidence(self):
        edit_criterion(self.out, "SE-03", absence_confirmed=True)
        self.assertIn("absence-unsupported", codes(self.out))

    def test_unknown_requires_discovery_attempts(self):
        edit_criterion(self.out, "EG-02", discovery_attempts=[])
        self.assertIn("unknown-without-attempts", codes(self.out))

    def test_five_requires_validation_evidence(self):
        edit_criterion(self.out, "PLT-02", maturity="5")
        self.assertIn("five-without-validation", codes(self.out))

    def test_score_requires_evidence(self):
        edit_criterion(self.out, "SE-03", evidence_refs=[])
        self.assertIn("score-without-evidence", codes(self.out))

    def test_confidence_none_cannot_support_score(self):
        edit_criterion(self.out, "SE-03", confidence="none")
        self.assertIn("score-without-confidence", codes(self.out))

    def test_not_applicable_needs_justification(self):
        edit_criterion(self.out, "KR-02", applicability_justification="")
        self.assertIn("na-unjustified", codes(self.out))

    def test_conflicting_needs_description(self):
        edit_criterion(self.out, "WRK-01", conflicting_evidence=[])
        self.assertIn("conflict-undescribed", codes(self.out))

    def test_not_investigated_blocks_unless_allowed(self):
        edit_criterion(self.out, "EG-02", discovery_coverage="not_investigated")
        self.assertIn("not-investigated", codes(self.out))
        self.assertNotIn("not-investigated", codes(self.out, allow_incomplete=True))
        self.assertIn("not-investigated", codes(self.out, level="warning", allow_incomplete=True))


if __name__ == "__main__":
    unittest.main()
