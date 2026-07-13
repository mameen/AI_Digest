"""Google ADK agent: ADK-compliant, Gemini API ranking."""

from __future__ import annotations

import os
from datetime import date
from typing import List

from src.base import Agent, NewsItem, BriefCard, DailyBrief
from src.fully_scripted.agent import _fetch_mvp_sources, _score_keyword


class GoogleADKAgent(Agent):
    """ADK-compliant agent using Google Gemini API for ranking."""

    def __init__(self):
        # Verify env var is set (required, read-only)
        if not os.getenv("GEMINI_API_KEY"):
            raise EnvironmentError("GEMINI_API_KEY env var not set")

    def discover(self) -> List[NewsItem]:
        """Discover stories (MVP: arXiv)."""
        print("\n[tool: discover]")
        items = _fetch_mvp_sources()
        print(f"  → {len(items)} items")
        return items

    def rank(self, items: List[NewsItem], count: int = 10) -> List[NewsItem]:
        """Rank using Gemini API."""
        print("\n[tool: rank]")

        try:
            import google.generativeai as genai

            # Load credentials from environment
            token = os.getenv("GEMINI_API_KEY")
            genai.configure(api_key=token)
            items_text = "\n".join(
                [f"{i + 1}. {item.title}" for i, item in enumerate(items)]
            )
            prompt = f"Rank these {len(items)} AI/ML stories (1=most important). Return ONLY comma-separated ranks:\n{items_text}"

            model = genai.GenerativeModel("gemini-pro")
            response = model.generate_content(prompt)
            ranks = [int(x.strip()) for x in response.text.strip().split(",")]

            ranked = [None] * len(items)
            for rank, item in zip(ranks, items):
                if 1 <= rank <= len(items):
                    ranked[rank - 1] = item

            result = [i for i in ranked if i is not None][:count]
            print(f"  → {len(result)} top items ranked (Gemini API) ✅")
            return result

        except Exception as e:
            print(f"  ⚠️  Gemini error: {str(e)[:60]}, falling back to keyword")
            return self._fallback_rank(items, count)

    def _fallback_rank(
        self, items: List[NewsItem], count: int = 10
    ) -> List[NewsItem]:
        """Fallback to keyword ranking if API fails."""
        ranked = sorted(
            items, key=lambda x: (-_score_keyword(x), x.title.lower())
        )
        return ranked[:count]

    def validate(self, items: List[NewsItem]) -> DailyBrief:
        """Validate brief schema."""
        print("\n[tool: validate]")

        if len(items) < 10:
            raise ValueError(f"Need 10 items, got {len(items)}")

        cards = [
            BriefCard(
                rank=i + 1,
                title=item.title,
                url=item.url,
                why_it_matters=item.summary[:200]
                if item.summary
                else "Key AI/ML story",
            )
            for i, item in enumerate(items[:10])
        ]

        brief = DailyBrief(
            date=str(date.today()),
            theme="AI signal over noise",
            cards=cards,
            schema_version="1.0",
        )

        print(f"  → {len(brief.cards)} cards validated ✅")
        return brief
