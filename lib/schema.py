"""Pydantic schema for Instructor / validation (matches digest JSON shape).

Organized as a hierarchy of domain models rather than flat functions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------

class ResourceLink(BaseModel):
    """A link to an external resource (GitHub, X, HuggingFace, etc.)."""

    name: str
    url: str
    kind: str | None = None  # github, x, linkedin, huggingface, arxiv, web


class Story(BaseModel):
    """Canonical story model — the atomic unit of the digest."""

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
    """A digest category containing zero or more stories."""

    id: str
    label: str
    icon: str
    stories: list[Story] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Enrichment models (used by the LLM response path)
# ---------------------------------------------------------------------------

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
    """A category with its enriched stories."""

    stories: list[StoryEnrich]


class GapCategories(BaseModel):
    """New editorial categories authored from ingestion context."""

    categories: list[Category]


# ---------------------------------------------------------------------------
# Top-level document models
# ---------------------------------------------------------------------------

class DigestDocument(BaseModel):
    """The complete digest output — the deterministic tail contract."""

    generated_at: str
    filename_prefix: str
    summary: str
    aisearch_video_url: str | None = None
    aisearch_video_label: str | None = None
    aisearch_video_description: str | None = None
    categories: list[Category]
    visualizations: dict[str, Any] | None = None


class DigestHeader(BaseModel):
    """Lightweight header for the digest report."""

    summary: str
    aisearch_video_url: str | None = None
    aisearch_video_label: str | None = None
    top_stories: list[Any] | None = None
    report_source: str | None = None
    report_source_badge: str | None = None
    report_source_label: str | None = None
