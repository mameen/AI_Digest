"""Extract bullets from a preflight skeleton category (already fetched in stage1)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from lib.ingest.types import IngestBundle, ResearchBullet, TopicResearch


def _url_ok(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    return bool((parsed.path or "").strip("/"))


def category_from_preflight(preflight: dict[str, Any], category_id: str) -> dict[str, Any] | None:
    for cat in preflight.get("categories") or []:
        if str(cat.get("id") or "") == category_id:
            return cat
    return None


def story_bullets_from_category(
    cat: dict[str, Any],
    *,
    include_episode: bool = False,
    channel_label: str | None = None,
    channel_url: str | None = None,
    max_bullets: int = 8,
) -> list[ResearchBullet]:
    """Generic story cards → ResearchBullet (works for robotics, typography, research, …)."""
    bullets: list[ResearchBullet] = []

    if include_episode:
        video_url = cat.get("_video_url") or cat.get("video_url")
        video_title = cat.get("_video_title") or cat.get("video_title") or cat.get("label")
        if video_url and _url_ok(str(video_url)):
            label = video_title or "Latest episode"
            bullets.append(ResearchBullet(title=f"**Episode:** {label}", url=str(video_url)))
        if channel_url and channel_label and _url_ok(channel_url):
            bullets.append(ResearchBullet(title=f"**Channel:** {channel_label}", url=channel_url))

    for story in cat.get("stories") or []:
        if not isinstance(story, dict):
            continue
        title = str(story.get("title") or "").strip()
        url = str(story.get("url") or "").strip()
        if title and _url_ok(url):
            bullets.append(ResearchBullet(title=title, url=url))
        if len(bullets) >= max_bullets:
            break
    return bullets


def research_from_preflight_category(
    bundle: IngestBundle,
    *,
    topic: str,
    category_id: str,
    seed: str,
    **kwargs: Any,
) -> TopicResearch:
    cat = category_from_preflight(bundle.preflight, category_id)
    bullets = story_bullets_from_category(cat or {}, **kwargs)
    return TopicResearch(
        topic=topic,
        bullets=bullets,
        seed=seed,
        preflight_prefix=bundle.prefix,
    )
