"""DEPRECATED: render — moved to lib/render.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/render.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.render is deprecated; import from lib.render instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.render import (  # noqa: F401,F403
    _ensure_scripts_path,
    _crawl_driven_leaderboards,
    build_content_html,
    rebuild_reports_archive,
    render,
)
