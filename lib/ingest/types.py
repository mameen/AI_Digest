"""Shared ingestion types for llm_pipeline and agentic/hermes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResearchBullet:
    """One citation line for researcher output.md / librarian merge."""

    title: str
    url: str
    verified: bool = True


@dataclass
class IngestBundle:
    """Stage-1 artifacts for one run prefix (preflight + leaderboard fetches)."""

    prefix: str
    preflight_path: Path
    preflight: dict[str, Any]
    crawl_paths: list[Path] = field(default_factory=list)
    structured_paths: list[Path] = field(default_factory=list)


@dataclass(frozen=True)
class TopicResearch:
    """Result of researching one digest target."""

    topic: str
    bullets: list[ResearchBullet]
    seed: str
    preflight_prefix: str | None = None
