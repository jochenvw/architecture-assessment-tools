"""Executing this file is a test failure: discovery must never run repository code."""
import os, pathlib, tempfile
pathlib.Path(os.environ.get("ADA_SENTINEL", tempfile.gettempdir() + "/ada-sentinel")).write_text("executed")
