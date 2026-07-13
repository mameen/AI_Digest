"""LangChain tools for Ollama agent (@tool decorated functions)."""

from __future__ import annotations

import dataclasses
import json
from typing import List

from langchain.tools import tool

from src.base import NewsItem, BriefCard, DailyBrief
from src.base.sources import fetch_all_sources
from src.base.utils import score_keyword


@tool
def discover(count: int = 100) -> str:
    """Discover recent AI/ML stories from all sources.
    
    Args:
        count: Number of stories to retrieve (default 100)
    
    Returns:
        JSON string with list of NewsItem records
    """
    items = fetch_all_sources()[:count]
    return json.dumps([dataclasses.asdict(item) for item in items])


@tool
def rank(items_json: str, count: int = 10) -> str:
    """Rank stories by importance.
    
    Args:
        items_json: JSON array of NewsItem records
        count: Number of top stories to return (default 10)
    
    Returns:
        JSON string with ranked items (top `count`)
    """
    items = [NewsItem(**item) for item in json.loads(items_json)]
    
    # Keyword-based ranking (fallback)
    ranked = sorted(items, key=lambda x: (-score_keyword(x), x.title.lower()))
    
    return json.dumps(
        [dataclasses.asdict(item) for item in ranked[:count]]
    )


@tool
def validate(cards_json: str) -> str:
    """Validate and finalize brief.
    
    Args:
        cards_json: JSON array of BriefCard records
    
    Returns:
        DailyBrief JSON
    """
    from datetime import date
    
    cards = [BriefCard(**card) for card in json.loads(cards_json)]
    
    if len(cards) != 10:
        raise ValueError(f"Need exactly 10 cards, got {len(cards)}")
    
    brief = DailyBrief(
        date=str(date.today()),
        theme="AI signal over noise",
        cards=cards,
        schema_version="1.0",
    )
    
    return json.dumps(dataclasses.asdict(brief))
