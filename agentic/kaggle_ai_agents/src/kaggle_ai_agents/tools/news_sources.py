"""Source adapters: config-driven source registry and normalization helpers.

Real sources are defined in config/project.yaml.  The fetch_stub_* helpers
below are *test fixtures only* — they are not the real source list.
"""

from __future__ import annotations

import yaml
from pathlib import Path

from kaggle_ai_agents.models import NewsItem


# ── Config-driven source registry ─────────────────────────────────────────────

def load_source_registry(config_path: str | Path | None = None) -> list[dict]:
    """Load the full source list from config/project.yaml."""
    if config_path is None:
        # tools/news_sources.py is 5 levels below kaggle_ai_agents root
        config_path = Path(__file__).parents[3] / "config" / "project.yaml"
    path = Path(config_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload.get("sources", [])


def sources_by_kind(kind: str, config_path: str | Path | None = None) -> list[dict]:
    """Return all source entries matching a given kind (rss, web_scrape, etc.)."""
    return [s for s in load_source_registry(config_path) if s.get("kind") == kind]


# ── Normalization ──────────────────────────────────────────────────────────────

def normalize_source_records(records: list[dict[str, str]]) -> list[NewsItem]:
    """Map heterogeneous fetch records into the shared NewsItem schema."""
    normalized: list[NewsItem] = []
    for record in records:
        title = record.get("title") or record.get("headline") or ""
        url = record.get("url") or record.get("source_url") or "https://example.com"
        summary = record.get("summary") or record.get("raw_excerpt") or ""
        normalized.append(
            NewsItem(
                source_id=record.get("source_id", "unknown"),
                title=title,
                url=url,
                summary=summary,
            )
        )
    return normalized


# ── Test fixtures (not real sources) ──────────────────────────────────────────

def _stub_source_records() -> list[dict[str, str]]:
    """Minimal heterogeneous records for unit tests — not the real source list."""
    return [
        {
            "source_id": "open-model-feed",
            "source_kind": "rss",
            "source_url": "https://example.com/open-model-benchmarks",
            "title": "Open model benchmarks improve",
            "summary": "New results show quality gains with lower latency.",
        },
        {
            "source_id": "interop-feed",
            "source_kind": "web",
            "source_url": "https://example.com/agent-tooling-standards",
            "headline": "Agent tooling standards emerging",
            "raw_excerpt": "Interoperability efforts reduce integration friction.",
        },
        {
            "source_id": "duplicate-host",
            "source_kind": "web",
            "source_url": "https://example.com/open-model-benchmarks?ref=dup",
            "title": "Open model benchmarks improve",
            "summary": "Duplicate candidate from another source.",
        },
    ]


def fetch_stub_items() -> list[NewsItem]:
    """Test fixture helper — returns normalized stub items for unit tests."""
    return normalize_source_records(_stub_source_records())


def fetch_contract_stub_items() -> list[NewsItem]:
    """Test fixture alias used in workflow tests."""
    return fetch_stub_items()
