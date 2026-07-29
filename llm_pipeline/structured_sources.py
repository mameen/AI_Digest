"""
Structured-API leaderboard sources.

.. deprecated::
    Moved to ``lib.structured_sources``. Import from there directly; this shim will be
    removed once the single-agent runtime proves parity via automated fixtures.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.structured_sources is deprecated; use lib.structured_sources instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.structured_sources import (  # noqa: F401
    STRUCTURED_SOURCES,
    evalplus_rows,
    swebench_rows,
    apply_structured_leaderboards,
)

__all__ = [
    "STRUCTURED_SOURCES",
    "evalplus_rows",
    "swebench_rows",
    "apply_structured_leaderboards",
]