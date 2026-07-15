"""Foundry estate assessment scanner.

A deterministic, resumable scanner for Azure AI Foundry estates. The scanner
performs inventory, evidence collection, rule evaluation and report generation.
It is bundled inside the ``foundry-estate-assessment`` Agent Skill and depends
only on the Python standard library plus the Azure CLI.
"""

__version__ = "1.0.1"
SCANNER_VERSION = __version__

__all__ = ["__version__", "SCANNER_VERSION"]
