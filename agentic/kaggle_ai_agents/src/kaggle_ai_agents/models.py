"""Core typed models for the news brief workflow."""

from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class NewsItem(BaseModel):
    source_id: str
    title: str
    url: HttpUrl
    summary: str = ""


class BriefCard(BaseModel):
    rank: int = Field(ge=1)
    title: str
    url: HttpUrl
    why_it_matters: str


class DailyBrief(BaseModel):
    date: str
    theme: str
    cards: list[BriefCard]
