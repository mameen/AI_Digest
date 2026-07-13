"""Ollama agent with LangChain prompt templates and chains."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.base import Agent, NewsItem, DailyBrief, BriefCard
from src.base.sources import fetch_all_sources
from src.base.utils import score_keyword


class OllamaAgent(Agent):
    """LangChain + Ollama chain-based agent (no ReAct)."""

    def __init__(
        self,
        model: str = "qwen2.5-coder:14b",
        host: str = "http://localhost:11434",
        verbose: bool = True,
    ):
        """Initialize Ollama agent.
        
        Args:
            model: Ollama model name
            host: Ollama server URL
            verbose: Print thinking steps
        """
        self.model = model
        self.host = host
        self.verbose = verbose
        self.llm = None
        self.chain = None
        self._init_llm()
        self._init_chain()

    def _init_llm(self):
        """Initialize ChatOllama LLM."""
        self.llm = ChatOllama(
            model=self.model,
            base_url=self.host,
            temperature=0.7,
            top_k=40,
            top_p=0.9,
        )
        if self.verbose:
            print(f"✅ Initialized ChatOllama: {self.model} @ {self.host}")

    def _init_chain(self):
        """Initialize LangChain prompt + parser chain."""
        prompt = PromptTemplate.from_template(
            """You are an AI/ML news curator. Given a list of stories, 
rank the top 10 most important for an AI/ML audience.

Consider: novelty, impact, technical depth, relevance to recent developments.

Stories to rank:
{stories_json}

Return a JSON array with exactly 10 items:
[
  {{"title": "...", "summary": "...", "source": "...", "relevance_score": 8}},
  ...
]"""
        )

        parser = JsonOutputParser()
        self.chain = prompt | self.llm | parser
        if self.verbose:
            print(f"✅ Initialized LangChain prompt + parser chain")

    def discover(self) -> list[NewsItem]:
        """Not used (chain pattern combines all steps)."""
        raise NotImplementedError("Use run() to execute full pipeline")

    def rank(self, items: list[NewsItem], count: int = 10) -> list[NewsItem]:
        """Not used (chain pattern combines all steps)."""
        raise NotImplementedError("Use run() to execute full pipeline")

    def validate(self, items: list[NewsItem]) -> DailyBrief:
        """Not used (chain pattern combines all steps)."""
        raise NotImplementedError("Use run() to execute full pipeline")

    def run(self) -> DailyBrief:
        """Execute full pipeline via LangChain chain.
        
        Returns:
            DailyBrief with 10 ranked stories
        """
        if self.verbose:
            print("\n[LangChain Chain Pipeline]")

        # Fetch all sources
        items = fetch_all_sources()
        if self.verbose:
            print(f"📰 Fetched {len(items)} items from all sources")

        # Pre-rank with keyword scoring
        ranked = sorted(
            items,
            key=lambda x: (-score_keyword(x), x.title.lower()),
        )[:15]  # Top 15 for LLM refinement

        # Prepare stories for LLM
        stories_json = json.dumps(
            [
                {
                    "title": item.title,
                    "source_id": item.source_id,
                    "summary": item.summary[:200],  # First 200 chars
                }
                for item in ranked
            ],
            indent=2,
        )

        if self.verbose:
            print(f"🧠 Invoking LLM to rank top {len(ranked)} stories...")

        try:
            # Invoke chain
            result = self.chain.invoke({"stories_json": stories_json})

            # Parse result
            cards = []
            for i, r in enumerate(result[:10]):  # Ensure exactly 10
                card = BriefCard(
                    rank=i + 1,
                    title=r.get("title", ""),
                    url=next(
                        (item.url for item in items if item.title == r.get("title")),
                        "https://example.com",
                    ),
                    why_it_matters=r.get("summary", r.get("content", "Key AI/ML story")),
                )
                cards.append(card)

            brief = DailyBrief(
                date=str(datetime.now(timezone.utc).date()),
                theme="AI signal over noise",
                cards=cards,
            )

            if self.verbose:
                print(f"✅ Generated brief with {len(brief.cards)} cards")

            return brief

        except Exception as e:
            if self.verbose:
                print(
                    f"⚠️  LLM ranking failed ({str(e)[:50]}), falling back to keyword ranking"
                )
            # Fallback: use keyword ranking
            cards = [
                BriefCard(
                    rank=i + 1,
                    title=item.title,
                    url=item.url,
                    why_it_matters=item.summary[:200] if item.summary else "Key AI/ML story",
                )
                for i, item in enumerate(ranked[:10])
            ]

            return DailyBrief(
                date=str(datetime.now(timezone.utc).date()),
                theme="AI signal over noise",
                cards=cards,
            )
