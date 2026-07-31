"""DEPRECATED: llm_client — moved to lib/llm_client.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/llm_client.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.llm_client is deprecated; import from lib.llm_client instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.llm_client import (  # noqa: F401,F403
    ensure_ollama_ready,
    make_client,
    make_raw_chat,
)
