"""DEPRECATED: validate — moved to lib/validate.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/validate.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.validate is deprecated; import from lib.validate instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.validate import (  # noqa: F401,F403
    apply_validation,
    validate_digest,
)
