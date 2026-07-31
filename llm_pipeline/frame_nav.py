"""DEPRECATED: frame_nav — moved to lib/frame_nav.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/frame_nav.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.frame_nav is deprecated; import from lib.frame_nav instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.frame_nav import (  # noqa: F401,F403
    ADMIN_INDEX,
    DIAGNOSTICS_ICON,
    DIAGNOSTICS_INDEX,
    FrameView,
    REPORTS_INDEX,
    admin_nav_enabled,
    diagnostics_available,
    frame_controls_html,
    frame_nav_css,
    frame_nav_html,
    inject_frame_nav,
)
