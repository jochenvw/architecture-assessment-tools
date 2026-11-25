"""Packaging: gates enforced, deterministic archive, working state excluded."""

from __future__ import annotations

import hashlib
import unittest
import zipfile

from _harness import TempDirTest, edit_criterion, load

from ada_lib import package


class PackageTest(TempDirTest):
    def test_builds_archive_without_working_state(self):
        out = self.copy_example()
        (out / "_work").mkdir()
        (out / "_work" / "alias-map.json").write_text("{}", encoding="utf-8")
        result = package.build(out)
        archive = out / "_dist" / result["archive"].replace("\\", "/").split("/")[-1]
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
        self.assertTrue(any(n.endswith("/manifest.json") for n in names))
        self.assertFalse(any("/_work/" in n or "/_dist/" in n for n in names))
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), result["sha256"])
        self.assertTrue(load(out, "manifest.json")["sanitisation"]["performed"])

    def test_refuses_when_gates_fail(self):
        out = self.copy_example()
        edit_criterion(out, "EG-02", status="unknown", maturity="0")
        with self.assertRaises(package.PackageError):
            package.build(out)
        self.assertFalse((out / "_dist").exists())


if __name__ == "__main__":
    unittest.main()
