"""Schema validation, reference resolution and the example package."""

from __future__ import annotations

import unittest

from _harness import EXAMPLE, TempDirTest, codes, load, save

from ada_lib import checks
from ada_lib.jsonschema_lite import load_schema, validate
from ada_lib.paths import JSON_FILES, SCHEMAS_DIR


class ExamplePackageTest(unittest.TestCase):
    def test_example_validates_against_every_schema(self):
        for name, schema in JSON_FILES.items():
            with self.subTest(file=name):
                errors = validate(load(EXAMPLE, name), load_schema(SCHEMAS_DIR / schema))
                self.assertEqual(errors, [], errors[:3])

    def test_example_passes_all_quality_gates(self):
        issues = checks.run(EXAMPLE)
        self.assertEqual([str(i) for i in issues if i.level in ("error", "warning")], [])


class SchemaFailureTest(TempDirTest):
    def test_invalid_enum_is_rejected(self):
        out = self.copy_example()
        ev = load(out, "evidence.json")
        ev["evidence"][0]["perspective"] = "guessed"
        save(out, "evidence.json", ev)
        self.assertIn("schema", codes(out))

    def test_absolute_evidence_path_is_rejected(self):
        out = self.copy_example()
        ev = load(out, "evidence.json")
        ev["evidence"][0]["location"]["path"] = "C:/Users/someone/repo/README.md"
        save(out, "evidence.json", ev)
        self.assertIn("schema", codes(out))


class ReferenceTest(TempDirTest):
    def test_unresolved_evidence_reference_fails(self):
        out = self.copy_example()
        a = load(out, "assessment.json")
        a["observations"][0]["evidence_refs"].append("EV-DOES-NOT-EXIST")
        save(out, "assessment.json", a)
        self.assertIn("unresolved-evidence", codes(out))

    def test_unresolved_entity_in_relationship_fails(self):
        out = self.copy_example()
        arch = load(out, "architecture.json")
        arch["relationships"][0]["target"] = "ENT-GHOST"
        save(out, "architecture.json", arch)
        self.assertIn("unresolved-entity", codes(out))

    def test_unresolved_flow_step_fails(self):
        out = self.copy_example()
        flows = load(out, "execution-flows.json")
        flows["flows"][0]["steps"][0]["next"] = ["S77"]
        save(out, "execution-flows.json", flows)
        self.assertIn("unresolved-step", codes(out))

    def test_missing_criterion_fails(self):
        out = self.copy_example()
        a = load(out, "assessment.json")
        a["criteria"] = [c for c in a["criteria"] if c["id"] != "EG-02"]
        save(out, "assessment.json", a)
        self.assertIn("criterion-missing", codes(out))

    def test_stale_rendered_files_fail(self):
        out = self.copy_example()
        a = load(out, "assessment.json")
        a["observations"][0]["observation"] = "Changed after rendering."
        save(out, "assessment.json", a)
        self.assertIn("render-stale", codes(out))


if __name__ == "__main__":
    unittest.main()
