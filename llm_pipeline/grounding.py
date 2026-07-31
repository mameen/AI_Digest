"""DEPRECATED: grounding — moved to lib/grounding.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/grounding.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.grounding is deprecated; import from lib.grounding instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.grounding import (  # noqa: F401,F403
    _EXEMPT_CATEGORY_IDS,
    annotate_ungrounded,
    collect_ingestion_urls,
    collect_roots,
    collect_skeleton_urls,
    find_ungrounded,
    is_ungrounded,
    normalize_url,
    strip_ungrounded,
)
