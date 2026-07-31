"""Stub: re-export from llm_pipeline.editorial until T2 extracts to lib/editorial.py."""

from llm_pipeline.editorial import (  # type: ignore[import-untyped]
    CANONICAL_ORDER,
    CATEGORY_CATALOG,
    category_id,
    load_editorial_brief,
)

__all__ = ["CANONICAL_ORDER", "CATEGORY_CATALOG", "category_id", "load_editorial_brief"]
