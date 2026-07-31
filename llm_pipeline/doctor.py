"""DEPRECATED: doctor — moved to lib/doctor.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/doctor.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.doctor is deprecated; import from lib.doctor instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.doctor import (  # noqa: F401,F403
    FAIL,
    OK,
    WARN,
    Check,
    DoctorReport,
    run_doctor,
)
