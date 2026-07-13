"""Abstract Agent base class for all implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from .models import NewsItem, DailyBrief


class Agent(ABC):
    """Base contract for all agent implementations.
    
    All three backends (fully_scripted, google_adk, ollama_agent) inherit from this.
    """

    @abstractmethod
    def discover(self) -> List[NewsItem]:
        """Step 1: Discover recent news items.
        
        Returns:
            List of NewsItem records (20-100 items typical)
        
        Raises:
            Exception: If discovery fails, caller should handle gracefully
        """
        pass

    @abstractmethod
    def rank(self, items: List[NewsItem], count: int = 10) -> List[NewsItem]:
        """Step 2: Rank items by importance, keep top `count`.
        
        Args:
            items: Unranked news items
            count: Number of top items to return (default 10 for final brief)
        
        Returns:
            Top `count` items, ranked by importance
        """
        pass

    @abstractmethod
    def validate(self, items: List[NewsItem]) -> DailyBrief:
        """Step 3: Validate and finalize brief.
        
        Args:
            items: Ranked items (typically 10)
        
        Returns:
            DailyBrief with exactly 10 BriefCard objects
        
        Raises:
            ValueError: If validation fails (e.g., wrong number of cards)
        """
        pass

    def run(self) -> DailyBrief:
        """Execute the full pipeline: discover → rank → validate.
        
        Returns:
            DailyBrief ready for output
        """
        items = self.discover()
        ranked = self.rank(items)
        brief = self.validate(ranked)
        return brief
