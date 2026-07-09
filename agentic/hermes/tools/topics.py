"""Demo research topics — single source for board, showcase, and provenance."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from lib.ingest.topics.registry import SourceKind, binding_for

_DEFAULT_TOPICS = ("aisearch", "leaderboard", "youtube")

_ROLES_PATH = Path(__file__).resolve().parents[1] / "admin" / "config" / "hermes_roles.yaml"


def load_demo_topics(roles: dict[str, Any] | None = None) -> list[str]:
    if roles is not None:
        topics = roles.get("demo_topics")
        if topics:
            return [str(t).strip().lower() for t in topics if str(t).strip()]
    if _ROLES_PATH.is_file():
        spec = yaml.safe_load(_ROLES_PATH.read_text(encoding="utf-8")) or {}
        topics = spec.get("demo_topics")
        if topics:
            return [str(t).strip().lower() for t in topics if str(t).strip()]
    return list(_DEFAULT_TOPICS)


def research_category_ids(roles: dict[str, Any] | None = None) -> frozenset[str]:
    return frozenset(load_demo_topics(roles))


def research_task_body(topic: str, *, prefix: str) -> str:
    """Kanban task body for a researcher worker — driven by topic registry."""
    binding = binding_for(topic)
    tool_lines = [
        "- `read_topic_config` (digest) — source binding for this topic",
        "- Hermes `web_search` (ddgs) to discover URLs when needed",
        "- `verify_url` (digest) on every URL before citing",
    ]
    if binding:
        if SourceKind.PREFLIGHT_CATEGORY in binding.kinds:
            cat = binding.preflight_category or binding.topic_id
            tool_lines.insert(
                1,
                f"- `read_preflight_category` (digest) category `{cat}` — lazy fetch on cache miss",
            )
        if SourceKind.RSS_FEEDS in binding.kinds:
            tool_lines.insert(
                -1,
                "- `fetch_rss` (digest) — omit feeds to use topic defaults",
            )
        if SourceKind.CRAWL_MARKDOWN in binding.kinds and binding.crawl_slugs:
            slug = binding.crawl_slugs[0]
            tool_lines.insert(
                -1,
                f"- `read_crawl_markdown` (digest) slug `{slug}` — lazy crawl on cache miss",
            )
        if SourceKind.STRUCTURED_JSON in binding.kinds and binding.structured_slugs:
            slug = binding.structured_slugs[0]
            tool_lines.insert(
                -1,
                f"- `read_structured_json` (digest) slug `{slug}` — lazy fetch on cache miss",
            )

    rubric = ""
    if binding and binding.rubric:
        rubric = f"\n\nTopic rubric: {binding.rubric}"

    return (
        f"Research **{topic}** for AI Digest (run prefix `{prefix}`).\n\n"
        f"**Step 1 (mandatory):** call `read_topic_config` with `topic` = `{topic}`.\n"
        f"**Step 2:** call `read_preflight_category` with `category_id` = `{topic}` "
        f"and `prefix` = `{prefix}` when the topic config lists preflight.\n\n"
        "Then gather sources:\n"
        + "\n".join(tool_lines)
        + "\n\nWrite **output.md** in your workspace: 3+ bullet lines, each with a "
        "verified `http` URL and a short summary. Handle errors (retry search, "
        "note gaps) — do not invent links."
        + rubric
        + "\n\n**Never call `kanban_block` for unknown topic** — the topic is "
        f"`{topic}`; retry tools with that id.\n\n"
        "Finish with `kanban_complete` and "
        'artifacts: ["<absolute-path>/output.md"]. '
        "Do not call kanban_block unless an external dependency is truly unavailable."
    )
