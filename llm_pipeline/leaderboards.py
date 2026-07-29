"""
Parse crawled leaderboard markdown into table rows.

.. deprecated::
    Moved to ``lib.leaderboards``. Import from there directly; this shim will be
    removed once the single-agent runtime proves parity via automated fixtures.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.leaderboards is deprecated; use lib.leaderboards instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.leaderboards import (  # noqa: F401
    AA_CRAWL_SLUG,
    ARENA_T2I_CRAWL_SLUG,
    parse_aa_models_md,
    parse_arena_image_md,
    arena_image_rows,
    aa_rows,
    _match_bracket,
    _key_span,
    render_rows_js,
    replace_field_array,
    set_field_string,
    apply_crawl_leaderboards,
)

__all__ = [
    "AA_CRAWL_SLUG",
    "ARENA_T2I_CRAWL_SLUG",
    "parse_aa_models_md",
    "parse_arena_image_md",
    "arena_image_rows",
    "aa_rows",
    "_match_bracket",
    "_key_span",
    "render_rows_js",
    "replace_field_array",
    "set_field_string",
    "apply_crawl_leaderboards",
]