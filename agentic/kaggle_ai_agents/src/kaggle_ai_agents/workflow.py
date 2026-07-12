"""Single-agent workflow stub for the capstone."""

from __future__ import annotations

from datetime import date

from kaggle_ai_agents.models import BriefCard, DailyBrief
from kaggle_ai_agents.tools.news_sources import fetch_stub_items


def run_daily_brief() -> DailyBrief:
    items = fetch_stub_items()
    cards = [
        BriefCard(rank=i + 1, title=item.title, url=item.url, why_it_matters=item.summary)
        for i, item in enumerate(items)
    ]
    return DailyBrief(date=str(date.today()), theme="AI signal over noise", cards=cards)
