"""DEPRECATED: history — moved to lib/history.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/history.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.history is deprecated; import from lib.history instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.history import (  # noqa: F401,F403
    format_prior_context,
    load_prior_digests,
)
