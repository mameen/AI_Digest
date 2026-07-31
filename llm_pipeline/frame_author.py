"""DEPRECATED: frame_author — moved to lib/frame_author.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/frame_author.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.frame_author is deprecated; import from lib.frame_author instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.frame_author import (  # noqa: F401,F403
    GITHUB_MARK,
    _author_photo_src,
    author_card_css,
    author_card_html,
    inject_author_card,
    sync_author_assets,
)
