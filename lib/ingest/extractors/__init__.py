"""Format/mechanism extractors — topic-agnostic utilities.

An **extractor** knows how to pull structured items from a *source kind* (RSS,
YouTube episode, crawl markdown, JSON API). It does **not** know about digest
category names like ``robotics`` or ``aisearch``.

Topic → extractor wiring lives in ``lib.ingest.topics.registry``.
"""

from lib.ingest.extractors.rss import FeedSpec, articles_to_bullets, fetch_feeds, parse_feed

__all__ = [
    "FeedSpec",
    "articles_to_bullets",
    "fetch_feeds",
    "parse_feed",
]
