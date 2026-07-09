"""Run shared stage-1 fetches once per agentic / pipeline run prefix."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lib.ingest.types import IngestBundle

_CACHE: dict[str, IngestBundle] = {}


def warm_bundle(cfg: dict[str, Any], prefix: str) -> IngestBundle:
    """Preflight skeleton + leaderboard crawl/structured fetch (cached per prefix)."""
    if prefix in _CACHE:
        return _CACHE[prefix]

    from lib.ingest.stage1 import crawl_leaderboards, fetch_structured_sources, run_preflight

    pfx, preflight_path = run_preflight(cfg, prefix=prefix)
    crawl_paths = crawl_leaderboards(cfg, pfx, preflight_path)
    structured_paths = fetch_structured_sources(cfg, pfx)
    bundle = IngestBundle(
        prefix=pfx,
        preflight_path=preflight_path,
        preflight=json.loads(preflight_path.read_text(encoding="utf-8")),
        crawl_paths=[Path(p) for p in crawl_paths],
        structured_paths=[Path(p) for p in structured_paths],
    )
    _CACHE[prefix] = bundle
    return bundle


def get_bundle(cfg: dict[str, Any], prefix: str) -> IngestBundle:
    """Return cached bundle or load from disk without fetching."""
    if prefix in _CACHE:
        return _CACHE[prefix]
    from lib.ingest.lazy import load_bundle

    bundle = load_bundle(cfg, prefix)
    _CACHE[prefix] = bundle
    return bundle


def put_bundle(bundle: IngestBundle) -> None:
    _CACHE[bundle.prefix] = bundle


def clear_bundle_cache() -> None:
    _CACHE.clear()
