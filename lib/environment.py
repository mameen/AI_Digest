"""Stub: re-export from llm_pipeline.environment until T2 extracts to lib/environment.py."""

from llm_pipeline.environment import (  # type: ignore[import-untyped]
    capture_environment,
    enrich_diagnostics_report,
)

__all__ = ["capture_environment", "enrich_diagnostics_report"]
