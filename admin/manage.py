#!/usr/bin/env python3
"""Backward-compatible entry — delegates to ``llm_pipeline/admin/manage.py``."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_RUNNER = Path(__file__).resolve().parents[1] / "llm_pipeline" / "admin" / "manage.py"

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(_RUNNER), *sys.argv[1:]]))
