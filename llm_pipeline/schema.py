"""Pydantic schema for Instructor / validation (matches digest JSON shape)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ResourceLink(BaseModel):
    name: str
    url: str
    kind: str | None = None  # github, x, linkedin, huggingface, arxiv, web


class Story(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    url: str | None = None
    significance: int = Field(ge=1, le=5)
    novelty: int = Field(ge=1, le=5)
    relevance_design: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None
    source_pending: bool = False
    provenance: str | None = None
    channel_key: str | None = None
    channel_label: str | None = None
    topic: str | None = None
    links: list[ResourceLink] = Field(default_factory=list)


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
    aisearch_video_description: str | None = None
    categories: list[Category]
    visualizations: dict[str, Any] | None = None
    top_stories: list[Any] | None = None
    report_source: str | None = None
    report_source_badge: str | None = None
    report_source_label: str | None = None


class StoryEnrich(BaseModel):
    """Enriched story; ids/urls preserved from preflight."""

    id: str
    title: str
    summary: str
    source: str
    url: str | None = None
    significance: int = Field(ge=1, le=5)
    novelty: int = Field(ge=1, le=5)
    relevance_design: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None
    source_pending: bool = False
    channel_key: str | None = None
    channel_label: str | None = None
    topic: str | None = None
    # NOTE: no `provenance` here on purpose — StoryEnrich is the LLM response
    # model. Provenance is deterministic pipeline metadata stamped after enrich
    # (see enrich._with_provenance); the model must never author it.


class CategoryStories(BaseModel):
    stories: list[StoryEnrich]


class GapCategories(BaseModel):
    """New editorial categories authored from ingestion context."""

    categories: list[Category]


class DigestHeader(BaseModel):
    summary: str
    aisearch_video_url: str | None = None
    aisearch_video_label: str | None = None
