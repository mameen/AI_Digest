"""Shared data models for all implementations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class NewsItem:
    """A single news story fetched from a source."""

    source_id: str
    title: str
    url: str
    summary: str = ""

    def __post_init__(self):
        if not self.url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {self.url}")


@dataclass
class BriefCard:
    """A ranked story card in the daily brief (1 of 10)."""

    rank: int  # 1-10 only
    title: str
    url: str
    why_it_matters: str

    def __post_init__(self):
        assert 1 <= self.rank <= 10, f"Rank must be 1-10, got {self.rank}"
        assert self.url.startswith("https://"), f"URL must be HTTPS: {self.url}"


@dataclass
class DailyBrief:
    """Final output: exactly 10 ranked stories with metadata."""

    date: str  # YYYY-MM-DD
    theme: str  # e.g. "AI signal over noise"
    cards: List[BriefCard]  # Exactly 10
    schema_version: str = "1.0"

    def __post_init__(self):
        assert len(self.cards) == 10, f"Must have exactly 10 cards, got {len(self.cards)}"
