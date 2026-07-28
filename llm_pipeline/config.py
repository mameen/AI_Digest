"""Configuration loader for ``config.yaml``, optional ``.env``, and LLM defaults.

.. deprecated::
    Moved to ``lib.config``. Import from there directly; this shim will be
    removed once the single-agent runtime proves parity via automated fixtures.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.config is deprecated; use lib.config instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.config import (  # noqa: F401
    Config,
    _apply_llm_defaults,
    _default_llm,
    load_config,
)

__all__ = ["load_config", "_default_llm", "_apply_llm_defaults", "Config"]
