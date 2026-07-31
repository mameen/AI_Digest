"""DEPRECATED: enrich — moved to lib/enrich.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/enrich.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.enrich is deprecated; import from lib.enrich instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.enrich import (  # noqa: F401,F403
    _apply_target_count,
    _categories_summary,
    _carry_forward_empty,
    _coerce_gap_categories,
    _ensure_scripts_path,
    _llm_call,
    _llm_category_enrich,
    _llm_gap_fill,
    _llm_leaderboard,
    _llm_summary,
    _llm_curate_category,
    _log_category_counts,
    _merge_skeleton_fields,
    _prior_category_stories,
    _promote_skeleton,
    _reattach_skeleton_links,
    _run_link_tool_loop,
    _skeleton_rules,
    _tool_loop_system,
    _tool_loop_user,
    _finalize_story_links,
    _with_provenance,
    enrich_digest,
    reattach_all_digest_links,
)
