"""JSON-shaped helpers for Hermes generic researcher tools."""

from __future__ import annotations

from typing import Any

from lib.ingest.bundle import put_bundle
from lib.ingest.extractors.crawl import read_crawl_markdown
from lib.ingest.extractors.preflight import bullets_from_bundle_category
from lib.ingest.extractors.rss import FeedSpec, articles_to_bullets, fetch_feeds
from lib.ingest.extractors.structured import read_structured_json
from lib.ingest.lazy import (
    ensure_crawl_slug,
    ensure_preflight,
    ensure_structured_slug,
    load_bundle,
)
from lib.ingest.topics.registry import binding_for, binding_to_dict
from lib.ingest.web import web_search


def fetch_rss(
    feeds: list[dict[str, Any]] | None = None,
    *,
    topic: str | None = None,
    title_fmt: str = "{source}: {title}",
) -> dict[str, Any]:
    """Fetch RSS/Atom feeds and return raw article dicts + optional bullets."""
    specs: list[FeedSpec] = []
    feed_rows = feeds or []
    if not feed_rows and topic:
        binding = binding_for(topic)
        if binding and binding.feeds:
            feed_rows = [
                {"label": f.label, "url": f.url, "limit": f.limit} for f in binding.feeds
            ]

    for row in feed_rows:
        label = str(row.get("label") or row.get("source") or "feed").strip()
        url = str(row.get("url") or "").strip()
        if not url:
            continue
        try:
            limit = int(row.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10
        specs.append(FeedSpec(label, url, limit))

    if not specs:
        return {"ok": False, "error": "at least one feed with url required (or pass topic with feeds)"}

    articles = fetch_feeds(specs)

    bullets = articles_to_bullets(articles, title_fmt=title_fmt)
    return {
        "ok": True,
        "feeds": len(specs),
        "articles": articles,
        "bullets": [{"title": b.title, "url": b.url} for b in bullets],
    }


def read_preflight_category(
    cfg: dict[str, Any],
    prefix: str,
    category_id: str,
    *,
    topic: str | None = None,
    max_bullets: int = 12,
) -> dict[str, Any]:
    """Read story stubs from a preflight skeleton category (lazy fetch on cache miss)."""
    cat_id = str(category_id or "").strip()
    if not cat_id:
        return {"ok": False, "error": "category_id required"}

    topic_key = topic or cat_id
    ensure_preflight(cfg, prefix, topic=topic_key)
    bundle = load_bundle(cfg, prefix)
    put_bundle(bundle)
    bullets = bullets_from_bundle_category(bundle, cat_id)[:max_bullets]
    return {
        "ok": True,
        "category_id": cat_id,
        "preflight_prefix": bundle.prefix,
        "bullets": [{"title": b.title, "url": b.url} for b in bullets],
        "seed": f"lib/ingest:preflight:{cat_id}",
    }


def read_crawl_markdown_tool(
    cfg: dict[str, Any],
    prefix: str,
    slug: str,
    *,
    topic: str | None = None,
    max_chars: int = 8000,
) -> dict[str, Any]:
    """Read crawl markdown from cache (lazy crawl/copy on miss)."""
    slug_key = str(slug or "").strip()
    if not slug_key:
        return {"ok": False, "error": "slug required"}

    path = ensure_crawl_slug(cfg, prefix, slug_key, topic=topic)
    bundle = load_bundle(cfg, prefix)
    put_bundle(bundle)
    text = read_crawl_markdown(cfg, bundle, slug_key)
    if not text:
        return {"ok": False, "error": f"crawl markdown not found: {slug_key}", "path": str(path or "")}

    excerpt = text[: max(1, int(max_chars))]
    return {
        "ok": True,
        "slug": slug_key,
        "path": str(path) if path else "",
        "chars": len(text),
        "markdown": excerpt,
        "truncated": len(text) > len(excerpt),
    }


def read_structured_json_tool(
    cfg: dict[str, Any],
    prefix: str,
    slug: str,
    *,
    topic: str | None = None,
) -> dict[str, Any]:
    """Read structured JSON from cache (lazy fetch/copy on miss)."""
    slug_key = str(slug or "").strip()
    if not slug_key:
        return {"ok": False, "error": "slug required"}

    path = ensure_structured_slug(cfg, prefix, slug_key, topic=topic)
    bundle = load_bundle(cfg, prefix)
    put_bundle(bundle)
    data = read_structured_json(cfg, bundle, slug_key)
    if data is None:
        return {"ok": False, "error": f"structured json not found: {slug_key}", "path": str(path or "")}

    return {
        "ok": True,
        "slug": slug_key,
        "path": str(path) if path else "",
        "data": data,
    }


def read_topic_config(topic: str) -> dict[str, Any]:
    """Return registry binding for a standing topic (tool hints for researchers)."""
    key = str(topic or "").strip().lower()
    if not key:
        return {"ok": False, "error": "topic required"}
    binding = binding_for(key)
    if binding is None:
        return {"ok": False, "error": f"unknown topic: {key}"}
    return {"ok": True, "topic": key, "config": binding_to_dict(binding)}


def web_search_topic(query: str, *, limit: int = 5) -> dict[str, Any]:
    """DDGS web search — LLM filters and verifies URLs before citing."""
    q = str(query or "").strip()
    if not q:
        return {"ok": False, "error": "query required"}
    try:
        n = int(limit)
    except (TypeError, ValueError):
        n = 5
    result = web_search(q, limit=max(1, min(n, 10)))
    return {"ok": True, "query": q, **result}
