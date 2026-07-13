"""Shared utilities for all backends."""

from src.base import NewsItem


def score_keyword(item: NewsItem) -> int:
    """Keyword-based scoring (fallback when no LLM available)."""
    score = 0
    text = f"{item.title} {item.summary}".lower()

    # High-priority keywords (+3)
    if any(k in text for k in ["model", "llm", "agent", "reasoning", "benchmark", "eval"]):
        score += 3

    # Medium-priority keywords (+2)
    if any(k in text for k in ["ai", "ml", "learning", "neural", "deep"]):
        score += 2

    # Low-priority keywords (+1)
    if any(k in text for k in ["training", "data", "algorithm"]):
        score += 1

    return score
