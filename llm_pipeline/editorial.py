"""DEPRECATED: editorial — moved to lib/editorial.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/editorial.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.editorial is deprecated; import from lib.editorial instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.editorial import (  # noqa: F401,F403
    BRIEF_PATH,
    CANONICAL_ORDER,
    CATEGORY_CATALOG,
    GAP_CATEGORY_IDS,
    SKELETON_CATEGORY_IDS,
    build_ingestion_context,
    category_id,
    category_targets,
    enrich_cfg,
    extract_aisearch_description,
    extract_aisearch_meta,
    extract_youtube_category,
    format_youtube_ingestion_block,
    load_editorial_brief,
    make_category,
    normalize_category_metadata,
    normalize_preflight_category,
    order_categories,
    skeleton_category_map,
    stories_for_prompt,
    strip_private_fields,
    target_for,
    DEFAULT_CATEGORY_TARGETS,
)
