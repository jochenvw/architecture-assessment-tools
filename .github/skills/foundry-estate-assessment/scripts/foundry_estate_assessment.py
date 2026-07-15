#!/usr/bin/env python3
"""Entry point for the foundry-estate-assessment scanner.

This thin wrapper makes the bundled ``src`` package importable so the skill is
fully self-contained: the customer does not install a separate scanner.

Usage:
    python scripts/foundry_estate_assessment.py <command> [options]

Commands: doctor, inventory, scan, resume, status, report, reevaluate, refresh
Run any command with --help for its options.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from foundry_estate_assessment.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
