"""Compose researcher bullets from topic bindings + generic extractors only.

No topic-specific Python composers — bindings select extractors; the LLM
(librarian / synthesizer) closes interpretation and narrative gaps.
"""

from __future__ import annotations

from typing import Any

from lib.ingest.extractors.crawl import bullets_from_aa_crawl
from lib.ingest.extractors.preflight import bullets_from_bundle_category
from lib.ingest.extractors.rss import articles_to_bullets, fetch_feeds
from lib.ingest.extractors.structured import bullets_from_structured_json
from lib.ingest.topics.registry import SourceKind, TopicBinding
from lib.ingest.types import IngestBundle, ResearchBullet, TopicResearch


def seed_for_binding(binding: TopicBinding) -> str:
    """Deterministic seed label for a binding (no I/O)."""
    seeds: list[str] = []
    if SourceKind.PREFLIGHT_CATEGORY in binding.kinds:
        cat_id = binding.preflight_category or binding.topic_id
        seeds.append(f"preflight:{cat_id}")
    if SourceKind.RSS_FEEDS in binding.kinds and binding.feeds:
        seeds.append("rss_feeds")
    if SourceKind.CRAWL_MARKDOWN in binding.kinds:
        seeds.append("crawl_markdown")
    if SourceKind.STRUCTURED_JSON in binding.kinds:
        seeds.append("structured_json")
    return "lib/ingest:" + "+".join(seeds) if seeds else "lib/ingest:none"


def compose_bullets(
    cfg: dict[str, Any],
    bundle: IngestBundle,
    binding: TopicBinding,
) -> tuple[list[ResearchBullet], str]:
    """Run all extractors listed in *binding*; return bullets + seed trace."""
    bullets: list[ResearchBullet] = []
    seeds: list[str] = []

    if SourceKind.PREFLIGHT_CATEGORY in binding.kinds:
        cat_id = binding.preflight_category or binding.topic_id
        part = bullets_from_bundle_category(bundle, cat_id)
        if part:
            bullets.extend(part)
            seeds.append(f"preflight:{cat_id}")

    if SourceKind.RSS_FEEDS in binding.kinds and binding.feeds:
        articles = fetch_feeds(list(binding.feeds))
        part = articles_to_bullets(articles, title_fmt="{source}: {title}")
        if part:
            bullets.extend(part)
            seeds.append("rss_feeds")

    if SourceKind.CRAWL_MARKDOWN in binding.kinds:
        part = bullets_from_aa_crawl(cfg, bundle)
        if part:
            bullets.extend(part)
            seeds.append("crawl_markdown")

    if SourceKind.STRUCTURED_JSON in binding.kinds:
        part = bullets_from_structured_json(cfg, bundle)
        if part:
            bullets.extend(part)
            seeds.append("structured_json")

    seed = "lib/ingest:" + "+".join(seeds) if seeds else "lib/ingest:none"
    return bullets, seed


def research_from_binding(
    cfg: dict[str, Any],
    bundle: IngestBundle,
    binding: TopicBinding,
) -> TopicResearch:
    bullets, seed = compose_bullets(cfg, bundle, binding)
    return TopicResearch(
        topic=binding.topic_id,
        bullets=bullets,
        seed=seed,
        preflight_prefix=bundle.prefix,
    )
