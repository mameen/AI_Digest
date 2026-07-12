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
    """Score an item based on relevance keywords.
    
    Higher scores indicate higher relevance to AI/ML topics.
    Score ranges from 0 to ~15 based on keyword presence.
    """
    score = 0
    text = f"{item.title} {item.summary}".lower()
    
    # Core AI/ML concepts (high relevance)
    if any(kw in text for kw in ["model", "llm", "language model", "transformer", "agent", "reasoning"]):
        score += 3
    if any(kw in text for kw in ["benchmark", "leaderboard", "evaluation", "eval"]):
        score += 3
    if any(kw in text for kw in ["ai", "artificial intelligence"]):
        score += 2
    
    # Task-specific concepts (medium relevance)
    if any(kw in text for kw in ["prompt", "fine-tune", "training", "dataset", "federated"]):
        score += 2
    if any(kw in text for kw in ["safety", "alignment", "bias", "fairness", "interpretability"]):
        score += 2
    
    # Supporting keywords (low relevance)
    if any(kw in text for kw in ["algorithm", "performance", "optimization", "efficiency"]):
        score += 1
    if any(kw in text for kw in ["new", "novel", "latest", "breakthrough"]):
        score += 1
    
    # Baseline: has content
    if item.summary:
        score += 1
    
    return score


def rank_items(items: list[NewsItem], limit: int = 10) -> list[NewsItem]:
    """Rank items by relevance and return top N (default 10)."""
    unique = dedupe_items(items)
    ranked = sorted(unique, key=lambda item: (-score_item(item), item.title.lower()))
    return ranked[:limit]
