"""Shared helpers. Tests run offline: no Azure, no network, stdlib only."""

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))

from ada_lib import checks  # noqa: E402

EXAMPLE = SKILL / "examples" / "contoso-claims-review"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TempDirTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ada-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def copy_example(self) -> Path:
        out = self.tmp / "pkg"
        shutil.copytree(EXAMPLE, out)
        return out

    def copy_fixture(self, name: str) -> Path:
        dst = self.tmp / name
        shutil.copytree(FIXTURES / name, dst)
        return dst


def load(out: Path, name: str):
    return json.loads((out / name).read_text(encoding="utf-8"))


def save(out: Path, name: str, data) -> None:
    (out / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def codes(out: Path, level: str = "error", **kw) -> set[str]:
    return {i.code for i in checks.run(out, **kw) if i.level == level}


def edit_criterion(out: Path, cid: str, **fields) -> None:
    doc = load(out, "assessment.json")
    for c in doc["criteria"]:
        if c["id"] == cid:
            c.update(copy.deepcopy(fields))
            break
    else:
        raise KeyError(cid)
    save(out, "assessment.json", doc)
