"""DEPRECATED: diagnostics — moved to lib/diagnostics.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/diagnostics.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.diagnostics is deprecated; import from lib.diagnostics instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.diagnostics import (  # noqa: F401,F403
    CrawlRecord,
    DiagnosticCollector,
    LlmCallRecord,
    LogRecord,
    StageRecord,
    ToolCallRecord,
    _NULL,
    _enrich_report_paths,
    _ms_to_label,
    _failed_stages,
    _normalize_tokens,
    _raw_llm_call,
    _extract_openai_usage,
    _render_run_log,
    _render_waterfall_html,
    _call_table_row,
    backfill_diagnostics_json_files,
    finish_collector,
    get_collector,
    init_collector,
    instrumented_llm_call,
    log,
    rebuild_diagnostics_waterfall_pages,
    _raw_llm_call_with_usage,
    diagnostics_dir,
)
