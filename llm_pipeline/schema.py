"""Pydantic schema for Instructor / validation (matches digest JSON shape).

.. deprecated::
    Moved to ``lib.schema``. Import from there directly; this shim will be
    removed once the single-agent runtime proves parity via automated fixtures.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.schema is deprecated; use lib.schema instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.schema import (  # noqa: F401
    Category,
    CategoryStories,
    DigestDocument,
    DigestHeader,
    GapCategories,
    ResourceLink,
    Story,
    StoryEnrich,
)

__all__ = [
    "ResourceLink",
    "Story",
    "Category",
    "DigestDocument",
    "StoryEnrich",
    "CategoryStories",
    "GapCategories",
    "DigestHeader",
]
