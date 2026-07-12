"""Deterministic Day 2 selection helpers: dedupe, score, and rank."""

from __future__ import annotations

from urllib.parse import urlparse

from kaggle_ai_agents.models import NewsItem


def _dedupe_key(item: NewsItem) -> tuple[str, str]:
    host = urlparse(str(item.url)).netloc.lower()
    title = item.title.strip().lower()
    return (title, host)


def dedupe_items(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[tuple[str, str]] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = _dedupe_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def score_item(item: NewsItem) -> int:
    score = 0
    text = f"{item.title} {item.summary}".lower()
    if "benchmark" in text:
        score += 3
    if "standard" in text or "interoperability" in text:
        score += 2
    if item.summary:
        score += 1
    return score


def rank_items(items: list[NewsItem], limit: int = 5) -> list[NewsItem]:
    unique = dedupe_items(items)
    ranked = sorted(unique, key=lambda item: (-score_item(item), item.title.lower()))
    return ranked[:limit]
