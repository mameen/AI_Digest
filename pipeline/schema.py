"""Pydantic schema for Instructor / validation (matches digest JSON shape)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Story(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    url: str
    significance: int = Field(ge=1, le=5)
    novelty: int = Field(ge=1, le=5)
    relevance_design: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None


class Category(BaseModel):
    id: str
    label: str
    icon: str
    stories: list[Story] = Field(default_factory=list)


class DigestDocument(BaseModel):
    generated_at: str
    filename_prefix: str
    summary: str
    aisearch_video_url: str | None = None
    aisearch_video_label: str | None = None
    categories: list[Category]
    visualizations: dict[str, Any] | None = None
    top_stories: list[Any] | None = None


class StoryEnrich(BaseModel):
    """Enriched story; ids/urls preserved from preflight."""

    id: str
    title: str
    summary: str
    source: str
    url: str
    significance: int = Field(ge=1, le=5)
    novelty: int = Field(ge=1, le=5)
    relevance_design: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None


class CategoryStories(BaseModel):
    stories: list[StoryEnrich]


class GapCategories(BaseModel):
    """New editorial categories authored from ingestion context."""

    categories: list[Category]


class DigestHeader(BaseModel):
    summary: str
    aisearch_video_url: str | None = None
    aisearch_video_label: str | None = None
