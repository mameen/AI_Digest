"""
Prompt-registered tool-calling loop for grounding gap-filled stories.

.. deprecated::
    Moved to ``lib.tools``. Import from there directly; this shim will be
    removed once the single-agent runtime proves parity via automated fixtures.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.tools is deprecated; use lib.tools instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.tools import (  # noqa: F401
    TOOL_CATALOG,
    ToolAction,
    format_tool_result,
    parse_ddg_results,
    parse_tool_action,
    run_tool_loop,
    verify_url,
    web_search,
)

__all__ = [
    "TOOL_CATALOG",
    "ToolAction",
    "format_tool_result",
    "parse_ddg_results",
    "parse_tool_action",
    "run_tool_loop",
    "verify_url",
    "web_search",
]