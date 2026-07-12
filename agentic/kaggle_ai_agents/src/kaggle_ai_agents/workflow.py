"""Single-agent workflow stub for the capstone.

This module provides two implementations:
1. run_daily_brief() - Scripted orchestration (deterministic, fast tests)
2. run_daily_brief_with_agent() - ADK agent-driven (intent-based, extensible)

Both produce the same DailyBrief output; the agent version demonstrates
how to scale from hardcoded logic to LLM-driven reasoning.
"""

from __future__ import annotations

from datetime import date

from kaggle_ai_agents.models import BriefCard, DailyBrief
from kaggle_ai_agents.tools.news_sources import discover_items, fetch_contract_stub_items
from kaggle_ai_agents.tools.selection import rank_items


def run_daily_brief(use_real_sources: bool = False) -> DailyBrief:
    """Run the daily brief workflow.
    
    Args:
        use_real_sources: If True, fetch from configured sources via discover.py.
                         If False, use stub data (for fast tests).
    """
    # Phase 1: Source discovery
    if use_real_sources:
        items = discover_items()
    else:
        items = fetch_contract_stub_items()
    
    # Phase 2: Deduplication and ranking
    ranked_items = rank_items(items)
    
    # Phase 3: Brief synthesis
    cards = [
        BriefCard(rank=i + 1, title=item.title, url=item.url, why_it_matters=item.summary)
        for i, item in enumerate(ranked_items)
    ]
    return DailyBrief(date=str(date.today()), theme="AI signal over noise", cards=cards)


def run_daily_brief_with_agent(use_real_sources: bool = True) -> DailyBrief:
    """Run the daily brief workflow using an ADK agent orchestrator.
    
    This version demonstrates the course's recommended approach:
    - Single agent with instruction
    - Skills as tools
    - Intent-driven orchestration
    
    Args:
        use_real_sources: If True (default), agent fetches from real sources.
                         If False, uses stub data (for fast testing).
    
    Returns:
        DailyBrief: Curated 10-card brief
    """
    from kaggle_ai_agents.adk_agent import create_agent
    
    agent = create_agent(
        name="ai_digest",
        instruction=(
            "You are an AI news curator. Discover the latest AI/ML stories from all "
            "configured sources, deduplicate, rank by importance, and produce a "
            "10-card curated brief. Explain why each story matters."
        ),
    )
    
    # The agent orchestrates tools in logical sequence
    prompt = "Generate today's AI digest from all sources" if use_real_sources else "Use stub data"
    brief = agent.forward(prompt)
    return brief
