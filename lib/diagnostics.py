"""Stub: re-export from llm_pipeline.diagnostics until T2 extracts to lib/diagnostics.py."""

from llm_pipeline.diagnostics import (  # type: ignore[import-untyped]
    finish_collector,
    get_collector,
    init_collector,
    instrumented_llm_call,
    log,
)

__all__ = ["finish_collector", "get_collector", "init_collector", "instrumented_llm_call", "log"]
