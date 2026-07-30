"""Shared code for llm_pipeline and agentic/hermes.

Public namespace — import from here after Track 2 extraction:
    from lib import schema, config, paths
"""

from __future__ import annotations

# Track 2: extracted from llm_pipeline/
from lib.config import Config, _apply_llm_defaults, _default_llm, load_config  # noqa: F401
from lib.dates import RunWindow, parse_start, prefix_for_start, build_run_window  # noqa: F401
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
)
from lib.paths import (  # noqa: F401
    AGENTIC_ROOT,
    LLM_PIPELINE_ROOT,
    REPO_ROOT,
    WEB_ROOT,
    LIB_DIR,
    VENDOR_DIR,
    SKILL_SCRIPTS,
    SKILL_DIR,
    cache_dir,
    diagnostics_dir,
    output_root,
    preflight_dir,
    reports_dir,
)
from lib.schema import (  # noqa: F401
    Category,
    CategoryStories,
    DigestDocument,
    DigestHeader,
    GapCategories,
    ResourceLink,
    Story,
    StoryEnrich,
)
from lib.structured_sources import (  # noqa: F401
    STRUCTURED_SOURCES,
    evalplus_rows,
    swebench_rows,
    apply_structured_leaderboards,
)
from lib.tools import (  # noqa: F401
    TOOL_CATALOG,
    ToolAction,
    format_tool_result,
    looks_not_found,
    parse_ddg_results,
    parse_tool_action,
    run_tool_loop,
    verify_url,
    web_search,
)

__all__ = [
    # config
    "load_config",
    "Config",
    # paths
    "REPO_ROOT",
    "LLM_PIPELINE_ROOT",
    "WEB_ROOT",
    "AGENTIC_ROOT",
    "LIB_DIR",
    "VENDOR_DIR",
    "SKILL_SCRIPTS",
    "SKILL_DIR",
    "cache_dir",
    "diagnostics_dir",
    "output_root",
    "preflight_dir",
    "reports_dir",
    # dates
    "RunWindow",
    "parse_start",
    "prefix_for_start",
    "build_run_window",
    # schema
    "ResourceLink",
    "Story",
    "Category",
    "DigestDocument",
    "DigestHeader",
    "CategoryStories",
    "GapCategories",
    "StoryEnrich",
    # leaderboards
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
    # structured_sources
    "STRUCTURED_SOURCES",
    "evalplus_rows",
    "swebench_rows",
    "apply_structured_leaderboards",
    # tools
    "TOOL_CATALOG",
    "ToolAction",
    "format_tool_result",
    "looks_not_found",
    "parse_ddg_results",
    "parse_tool_action",
    "run_tool_loop",
    "verify_url",
    "web_search",
]
