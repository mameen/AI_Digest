"""Shared code for llm_pipeline and agentic/hermes.

Public namespace — import from here after Track 2 extraction:
    from lib import schema, config, paths
"""

from __future__ import annotations

# Track 2: extracted from llm_pipeline/
from lib.config import Config, _apply_llm_defaults, _default_llm, load_config  # noqa: F401
from lib.paths import (  # noqa: F401
    AGENTIC_ROOT,
    LLM_PIPELINE_ROOT,
    REPO_ROOT,
    WEB_ROOT,
)
from lib.schema import (  # noqa: F401
    Category,
    DigestDocument,
    ResourceLink,
    Story,
)

__all__ = [
    "load_config",
    "Config",
    "REPO_ROOT",
    "LLM_PIPELINE_ROOT",
    "WEB_ROOT",
    "AGENTIC_ROOT",
    "ResourceLink",
    "Story",
    "Category",
    "DigestDocument",
]
