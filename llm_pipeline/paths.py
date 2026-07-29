"""
Path layout for the staged digest pipeline.

.. deprecated::
    Moved to ``lib.paths``. Import from there directly; this shim will be
    removed once the single-agent runtime proves parity via automated fixtures.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.paths is deprecated; use lib.paths instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.paths import (  # noqa: F401
    AGENTIC_ROOT,
    LLM_PIPELINE_ROOT,
    REPO_ROOT,
    WEB_ROOT,
    LIB_DIR,
    VENDOR_DIR,
    SKILL_SCRIPTS,
    SKILL_DIR,
    cache_dir,
    diagnostics_dir,
    output_root,
    preflight_dir,
    reports_dir,
)

__all__ = [
    "AGENTIC_ROOT",
    "LLM_PIPELINE_ROOT",
    "REPO_ROOT",
    "WEB_ROOT",
    "LIB_DIR",
    "VENDOR_DIR",
    "SKILL_SCRIPTS",
    "SKILL_DIR",
    "cache_dir",
    "diagnostics_dir",
    "output_root",
    "preflight_dir",
    "reports_dir",
]
