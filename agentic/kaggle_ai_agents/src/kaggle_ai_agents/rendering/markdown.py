"""Markdown renderer for the daily brief."""

from __future__ import annotations

from kaggle_ai_agents.models import DailyBrief


def render_markdown(brief: DailyBrief) -> str:
    lines = [f"# Daily AI Brief ({brief.date})", "", f"Theme: {brief.theme}", ""]
    for card in brief.cards:
        lines.append(f"{card.rank}. [{card.title}]({card.url})")
        lines.append(f"   - Why it matters: {card.why_it_matters}")
    return "\n".join(lines) + "\n"
