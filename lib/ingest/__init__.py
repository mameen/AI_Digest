"""Shared ingestion for llm_pipeline and agentic/hermes.

Source kinds live under ``lib/ingest/extractors/`` and ``compose.py``.
Stage-1 batch fetch: ``warm_bundle()`` → ``stage1``.

Hermes workers use digest-tools: ``verify_url``, ``fetch_rss``,
``read_preflight_category``; search via Hermes ``web_search`` (ddgs).
"""

from lib.ingest.aisearch import SEED as AISEARCH_SEED
from lib.ingest.bundle import clear_bundle_cache, warm_bundle
from lib.ingest.dispatch import research_topic, seed_topic_workspace
from lib.ingest.leaderboard import SEED as LEADERBOARD_SEED
from lib.ingest.stage1 import crawl_leaderboards, fetch_structured_sources, run_preflight
from lib.ingest.types import IngestBundle, ResearchBullet, TopicResearch

__all__ = [
    "AISEARCH_SEED",
    "LEADERBOARD_SEED",
    "IngestBundle",
    "ResearchBullet",
    "TopicResearch",
    "clear_bundle_cache",
    "crawl_leaderboards",
    "fetch_structured_sources",
    "research_topic",
    "run_preflight",
    "seed_topic_workspace",
    "warm_bundle",
]
