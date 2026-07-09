"""Hermes wrapper — re-exports lib.ingest bundle cache for handover."""

from __future__ import annotations

from typing import Any

from lib.ingest.bundle import warm_bundle as warm_ingest_cache
from lib.ingest.fixtures import fixture_path

from tools.baseline import default_config


def get_ingest(cfg: dict[str, Any] | None, prefix: str) -> dict[str, Any]:
    """Legacy dict shape for handover_trace until migrated to IngestBundle."""
    bundle = warm_ingest_cache(cfg or default_config(), prefix)
    return {
        "prefix": bundle.prefix,
        "preflight_path": bundle.preflight_path,
        "preflight": bundle.preflight,
        "crawl_paths": bundle.crawl_paths,
        "structured_paths": bundle.structured_paths,
    }


__all__ = ["fixture_path", "get_ingest", "warm_ingest_cache"]
