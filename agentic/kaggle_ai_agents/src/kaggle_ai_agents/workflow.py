"""Single-agent workflow stub for the capstone."""

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
