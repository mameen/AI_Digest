"""Schema checks for output artifacts."""

from __future__ import annotations

from kaggle_ai_agents.models import DailyBrief


def validate_brief(data: dict) -> DailyBrief:
    return DailyBrief.model_validate(data)
