"""Profiles and catalogue: composition, validation, YAML subset parity."""

from __future__ import annotations

import unittest

from _harness import TempDirTest

from ada_lib import catalogue, profiles, yaml_lite
from ada_lib.paths import DOMAIN_TITLES, PROFILES_DIR

EXAMPLES = ["azure-agent", "example-platform", "example-document-review"]


class CatalogueTest(unittest.TestCase):
    def test_twelve_domains_unique_ids(self):
        crits = catalogue.load_catalogue()
        self.assertEqual({c.domain for c in crits}, set(DOMAIN_TITLES))
        ids = [c.id for c in crits]
        self.assertEqual(len(ids), len(set(ids)))


class ProfileTest(TempDirTest):
    def test_shipped_profiles_parse_identically_without_pyyaml(self):
        try:
            import yaml  # type: ignore
        except ImportError:
            self.skipTest("PyYAML not installed; parity check needs it")
        for path in sorted(PROFILES_DIR.rglob("*.yaml")):
            with self.subTest(profile=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(yaml_lite._MiniYaml(text).parse(), yaml.safe_load(text))

    def test_composition_adds_criteria_and_emphasis(self):
        base = profiles.resolve(["azure-agent"])
        combined = profiles.resolve(EXAMPLES)
        self.assertGreater(len(combined.criteria), len(base.criteria))
        self.assertEqual([p.kind for p in combined.profiles], ["generic", "platform", "workload"])
        self.assertTrue(any(c.source_profile == "example-document-review" for c in combined.criteria))
        self.assertIn(combined.domain_emphasis.get("08"), ("high", "critical"))
        self.assertTrue(combined.briefing)

    def test_order_independent(self):
        a = profiles.resolve(EXAMPLES)
        b = profiles.resolve(list(reversed(EXAMPLES)))
        self.assertEqual([c.id for c in a.criteria], [c.id for c in b.criteria])

    def test_missing_required_profile_fails(self):
        with self.assertRaises(profiles.ProfileError):
            profiles.resolve(["example-document-review"])

    def test_unknown_profile_fails(self):
        with self.assertRaises(profiles.ProfileError):
            profiles.resolve(["azure-agent", "does-not-exist"])

    def test_colliding_criterion_ids_fail(self):
        src = (PROFILES_DIR / "examples" / "example-platform.yaml").read_text(encoding="utf-8")
        clone = self.tmp / "clone-platform.yaml"
        clone.write_text(src.replace("id: example-platform", "id: clone-platform"), encoding="utf-8")
        with self.assertRaises(profiles.ProfileError):
            profiles.resolve(["azure-agent", "example-platform", str(clone)])


if __name__ == "__main__":
    unittest.main()
