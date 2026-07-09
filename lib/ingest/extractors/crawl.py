"""Crawl markdown extractor — parse leaderboard tables from cached .md files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from llm_pipeline.leaderboards import AA_CRAWL_SLUG, parse_aa_models_md
from llm_pipeline.paths import cache_dir

from lib.ingest.fixtures import fixture_path
from lib.ingest.types import IngestBundle, ResearchBullet

AA_URL = "https://artificialanalysis.ai/leaderboards/models"


def _read_text(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def read_crawl_markdown(cfg: dict[str, Any], bundle: IngestBundle, slug: str) -> str | None:
    crawl_dir = cache_dir(cfg) / bundle.prefix / "crawl"
    text = _read_text(crawl_dir / slug)
    if text:
        return text
    for path in bundle.crawl_paths:
        if path.name == slug:
            return _read_text(path)
    return _read_text(fixture_path(slug))


def bullets_from_aa_crawl(cfg: dict[str, Any], bundle: IngestBundle, *, limit: int = 5) -> list[ResearchBullet]:
    """Top rows from Artificial Analysis intelligence crawl markdown."""
    md = read_crawl_markdown(cfg, bundle, AA_CRAWL_SLUG)
    if not md:
        return []
    bullets: list[ResearchBullet] = []
    for i, row in enumerate(parse_aa_models_md(md)[:limit], start=1):
        model = row.get("model", "")
        provider = row.get("provider", "")
        intel = row.get("intelligence", "")
        bullets.append(
            ResearchBullet(
                title=f"AA Intelligence #{i}: {model} ({provider}, score {intel})",
                url=AA_URL,
            )
        )
    return bullets
