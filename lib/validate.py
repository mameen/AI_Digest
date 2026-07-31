"""Stub: re-export from llm_pipeline.validate until T2 extracts to lib/validate.py."""

from llm_pipeline.validate import (  # type: ignore[import-untyped]
    apply_validation,
    validate_digest,
)

__all__ = ["apply_validation", "validate_digest"]
