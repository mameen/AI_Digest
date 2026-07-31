"""DEPRECATED: site_footer — moved to lib/site_footer.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/site_footer.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.site_footer is deprecated; import from lib.site_footer instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.site_footer import (  # noqa: F401,F403
    inject_site_footer,
    site_footer_css,
    site_footer_html,
)
