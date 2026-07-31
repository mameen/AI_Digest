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
from lib.grounding import (  # noqa: F401
    normalize_url,
    collect_roots,
    annotate_ungrounded,
)
from lib.history import (  # noqa: 401
    load_prior_digests,
    format_prior_context,
)
from lib.llm_client import (  # noqa: F401
    ensure_ollama_ready,
    make_client,
    make_raw_chat,
)
from lib.visualize import (  # noqa: F401
    compute_visualizations,
    fill_skeleton_stories,
)
from lib.editorial import (  # noqa: F401
    CATEGORY_CATALOG,
    CANONICAL_ORDER,
    load_editorial_brief,
)
from lib.environment import (  # noqa: F401
    capture_environment,
    enrich_diagnostics_report,
)
from lib.doctor import (  # noqa: F401
    Check,
    DoctorReport,
    run_doctor,
)
from lib.frame_author import (  # noqa: F401
    GITHUB_MARK,
    author_card_html,
    inject_author_card,
    sync_author_assets,
)
from lib.frame_nav import (  # noqa: F401
    diagnostics_available,
    admin_nav_enabled,
    inject_frame_nav,
)
from lib.site_footer import (  # noqa: F401
    site_footer_html,
    inject_site_footer,
)
from lib.validate import (  # noqa: F401
    validate_digest,
    apply_validation,
)
from lib.diagnostics_frame import (  # noqa: F401
    build_diagnostics_index,
    rebuild_diagnostics_archive,
)
from lib.diagnostics import (  # noqa: F401
    DiagnosticCollector,
    instrumented_llm_call,
)
from lib.enrich import (  # noqa: F401
    enrich_digest,
    reattach_all_digest_links,
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
    # grounding
    "normalize_url",
    "collect_roots",
    "annotate_ungrounded",
    # history
    "load_prior_digests",
    "format_prior_context",
    # llm_client
    "ensure_ollama_ready",
    "make_client",
    "make_raw_chat",
    # visualize
    "compute_visualizations",
    "fill_skeleton_stories",
    # editorial
    "CATEGORY_CATALOG",
    "CANONICAL_ORDER",
    "load_editorial_brief",
    "format_editorial_context",
    # environment
    "capture_environment",
    "enrich_diagnostics_report",
    # doctor
    "Check",
    "DoctorReport",
    "run_doctor",
    # frame_author
    "GITHUB_MARK",
    "author_card_html",
    "inject_author_card",
    "sync_author_assets",
    # frame_nav
    "diagnostics_available",
    "admin_nav_enabled",
    "inject_frame_nav",
    # site_footer
    "site_footer_html",
    "inject_site_footer",
    # validate
    "validate_digest",
    "apply_validation",
    # diagnostics_frame
    "build_diagnostics_index",
    "rebuild_diagnostics_archive",
    # diagnostics
    "DiagnosticCollector",
    "instrumented_llm_call",
    "instrumented_fetch",
    "instrumented_enrichment",
    # enrich
    "enrich_digest",
    "reattach_all_digest_links",
]
