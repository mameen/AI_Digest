"""Backward-compatible re-exports — implementation lives in ``lib.ingest.stage1``."""

from lib.ingest.stage1 import crawl_leaderboards, fetch_structured_sources, run_preflight

__all__ = ["crawl_leaderboards", "fetch_structured_sources", "run_preflight"]
