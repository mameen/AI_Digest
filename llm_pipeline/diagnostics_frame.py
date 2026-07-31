"""DEPRECATED: diagnostics_frame — moved to lib/diagnostics_frame.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/diagnostics_frame.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.diagnostics_frame is deprecated; import from lib.diagnostics_frame instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.diagnostics_frame import (  # noqa: F401,F403
    _heat_color,
    _intensity_score,
    _ms_label,
    build_diagnostics_frame_html,
    build_diagnostics_index,
    diagnostics_index_entry,
    list_diagnostics_jsons,
    rebuild_diagnostics_archive,
)
