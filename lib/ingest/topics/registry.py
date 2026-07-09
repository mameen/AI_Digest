"""Topic → source binding — *what* to research, not *how* to parse it."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from lib.ingest.extractors.rss import FeedSpec
from llm_pipeline.leaderboards import AA_CRAWL_SLUG


class SourceKind(str, Enum):
    """Mechanism extractors — independent of editorial topic names."""

    PREFLIGHT_CATEGORY = "preflight_category"
    RSS_FEEDS = "rss_feeds"
    CRAWL_MARKDOWN = "crawl_markdown"
    STRUCTURED_JSON = "structured_json"
    WEB_SEARCH = "web_search"


@dataclass(frozen=True)
class TopicBinding:
    """Maps a digest topic (researcher task target) to one or more source kinds."""

    topic_id: str
    kinds: tuple[SourceKind, ...]
    # Preflight category id when kind includes PREFLIGHT_CATEGORY (often == topic_id)
    preflight_category: str | None = None
    # RSS feeds when kind includes RSS_FEEDS
    feeds: tuple[FeedSpec, ...] = ()
    crawl_slugs: tuple[str, ...] = ()
    structured_slugs: tuple[str, ...] = ()
    evaluation: bool = False
    rubric: str = ""


TOPIC_BINDINGS: dict[str, TopicBinding] = {
    "aisearch": TopicBinding(
        topic_id="aisearch",
        kinds=(SourceKind.PREFLIGHT_CATEGORY,),
        preflight_category="aisearch",
        rubric="Read the preflight aisearch skeleton; verify chapter URLs before citing.",
    ),
    "leaderboard": TopicBinding(
        topic_id="leaderboard",
        kinds=(SourceKind.CRAWL_MARKDOWN, SourceKind.STRUCTURED_JSON),
        crawl_slugs=(AA_CRAWL_SLUG,),
        structured_slugs=("swebench_leaderboards.json", "evalplus_results.json"),
        rubric="Combine AA crawl markdown with SWE-bench and EvalPlus JSON rows.",
    ),
    "youtube": TopicBinding(
        topic_id="youtube",
        kinds=(SourceKind.PREFLIGHT_CATEGORY,),
        preflight_category="youtube",
        rubric=(
            "Read the preflight youtube secondary-channel skeleton; verify each "
            "video URL before citing. Preserve channel_key when present."
        ),
    ),
    "robotics": TopicBinding(
        topic_id="robotics",
        kinds=(SourceKind.PREFLIGHT_CATEGORY, SourceKind.RSS_FEEDS),
        preflight_category="robotics",
        feeds=(
            FeedSpec("The Robot Report", "https://www.therobotreport.com/feed/", 10),
            FeedSpec("IEEE Spectrum Robotics", "https://spectrum.ieee.org/feeds/topic/robotics.rss", 10),
            FeedSpec("Robohub", "https://robohub.org/feed/", 10),
        ),
    ),
    "typography": TopicBinding(
        topic_id="typography",
        kinds=(SourceKind.PREFLIGHT_CATEGORY,),
        preflight_category="typography",
    ),
    "research": TopicBinding(
        topic_id="research",
        kinds=(SourceKind.PREFLIGHT_CATEGORY,),
        preflight_category="research",
    ),
    "evaluation_test_topic": TopicBinding(
        topic_id="evaluation_test_topic",
        kinds=(
            SourceKind.PREFLIGHT_CATEGORY,
            SourceKind.RSS_FEEDS,
            SourceKind.CRAWL_MARKDOWN,
            SourceKind.STRUCTURED_JSON,
            SourceKind.WEB_SEARCH,
        ),
        preflight_category="evaluation_test_topic",
        feeds=(FeedSpec("Eval fixture feed", "eval:test_feed.xml", 5),),
        crawl_slugs=(AA_CRAWL_SLUG,),
        structured_slugs=("swebench_leaderboards.json", "evalplus_results.json"),
        evaluation=True,
        rubric=(
            "Fixture-backed eval topic: exercise every digest tool without live network. "
            "Use read_topic_config first; lazy tools seed from tests/data/evaluation/."
        ),
    ),
}


def binding_for(topic: str) -> TopicBinding | None:
    return TOPIC_BINDINGS.get(topic.strip().lower())


def binding_to_dict(binding: TopicBinding) -> dict[str, Any]:
    """JSON-serializable topic config for researcher tools."""
    return {
        "topic_id": binding.topic_id,
        "kinds": [k.value for k in binding.kinds],
        "preflight_category": binding.preflight_category,
        "feeds": [
            {"label": f.label, "url": f.url, "limit": f.limit} for f in binding.feeds
        ],
        "crawl_slugs": list(binding.crawl_slugs),
        "structured_slugs": list(binding.structured_slugs),
        "evaluation": binding.evaluation,
        "rubric": binding.rubric,
    }
