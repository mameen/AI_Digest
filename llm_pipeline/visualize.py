"""DEPRECATED: visualize — moved to lib/visualize.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/visualize.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.visualize is deprecated; import from lib.visualize instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.visualize import (  # noqa: F401,F403
    compute_visualizations,
    fill_skeleton_stories,
)
