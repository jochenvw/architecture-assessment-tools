"""Regression tests for Windows-specific execution issues (GH issue #2).

1. The Azure CLI must be resolved through ``shutil.which`` so ``az.cmd`` is
   found on Windows (bare ``az`` is not resolved with ``shell=False``).
2. ``atomic_write`` must handle absolute paths longer than the classic
   ``MAX_PATH`` (260) limit.
"""

from __future__ import annotations

import os
import shutil
import unittest

import _harness  # noqa: F401  (path bootstrap)

from foundry_estate_assessment.azure_cli import SubprocessCommandRunner
from foundry_estate_assessment.evidence import _os_path, _safe_filename, atomic_write
from foundry_estate_assessment.models import TaskStatus
from foundry_estate_assessment.scheduler import classify_exception


class TestCliResolution(unittest.TestCase):
    def test_resolves_via_which_when_available(self):
        # A name that certainly resolves on every platform running the tests.
        exe = "python" if shutil.which("python") else "sh"
        resolved = shutil.which(exe)
        if resolved is None:  # pragma: no cover - environment dependent
            self.skipTest("no resolvable executable to probe")
        runner = SubprocessCommandRunner(exe)
        self.assertEqual(runner._az_path, resolved)

    def test_falls_back_to_name_when_unresolvable(self):
        runner = SubprocessCommandRunner("definitely-not-a-real-cli-xyz")
        self.assertEqual(runner._az_path, "definitely-not-a-real-cli-xyz")


class TestLongPathWrite(unittest.TestCase):
    def test_writes_beyond_max_path(self):
        import tempfile
        from pathlib import Path

        root = Path(tempfile.mkdtemp())
        long_id = (
            "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/"
            "rg-with-a-fairly-long-name/providers/Microsoft.CognitiveServices/"
            "accounts/some-foundry-account-name"
        )
        name = _safe_filename(long_id, "model_deployments")
        # Nest deeply so the absolute path is well over MAX_PATH.
        parts = ("aaaaaaaaaa", "bbbbbbbbbb", "cccccccccc", "dddddddddd", "eeeeeeeeee")
        deep = root
        for part in parts:
            deep = deep / part
        target = deep / name
        self.assertGreater(len(os.path.abspath(str(target)) + ".tmp"), 260)

        try:
            atomic_write(target, '{"ok": true}')
            # Path.exists()/read_text() themselves hit MAX_PATH, so verify via
            # the extended-length path the writer used.
            self.assertTrue(os.path.exists(_os_path(target)))
            with open(_os_path(target), "r", encoding="utf-8") as handle:
                self.assertEqual(handle.read(), '{"ok": true}')
        finally:
            # Long-path-aware cleanup (plain rmtree hits MAX_PATH on Windows).
            os.remove(_os_path(target))
            cur = deep
            for _ in range(len(parts)):
                os.rmdir(_os_path(cur))
                cur = cur.parent
            os.rmdir(_os_path(root))


class TestErrorClassification(unittest.TestCase):
    def test_local_os_errors_fail_hard_not_retryable(self):
        # A local IO failure (e.g. MAX_PATH) is deterministic; retrying it
        # forever would mask the cause, so it must map to FAILED.
        status, error_class, retry_after = classify_exception(
            FileNotFoundError(2, "No such file or directory")
        )
        self.assertEqual(status, TaskStatus.FAILED)
        self.assertEqual(error_class, "FileNotFoundError")
        self.assertIsNone(retry_after)


if __name__ == "__main__":
    unittest.main()
