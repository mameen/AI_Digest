"""
Digest run date and history window helpers.

.. deprecated::
    Moved to ``lib.dates``. Import from there directly; this shim will be
    removed once the single-agent runtime proves parity via automated fixtures.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.dates is deprecated; use lib.dates instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.dates import (  # noqa: F401
    RunWindow,
    parse_start,
    prefix_for_start,
    build_run_window,
)

__all__ = [
    "RunWindow",
    "parse_start",
    "prefix_for_start",
    "build_run_window",
]