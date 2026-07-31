"""DEPRECATED: environment — moved to lib/environment.py.

This shim exists only to avoid breaking existing imports during Track 2 extraction.
All code has been extracted to lib/environment.py. Import from there instead.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.environment is deprecated; import from lib.environment instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.environment import (  # noqa: F401,F403
    LEGACY_RTX4090_ENV,
    SCHEMA,
    backfill_environment,
    backfill_network,
    capture_environment,
    _env_populated,
    _run,
    _ram_gb,
    _cpu_label,
    _detect_cuda_gpu,
    _detect_mac_gpu,
    detect_platform_kind,
    enrich_diagnostics_report,
    format_env_line,
    format_net_line,
    hw_metric_cards,
    summarize_network,
    platform,
)
