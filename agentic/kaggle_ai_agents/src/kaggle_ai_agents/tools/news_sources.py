"""Deterministic source adapters used for local testing and contracts."""

from __future__ import annotations

from kaggle_ai_agents.models import NewsItem


def fetch_stub_source_records() -> list[dict[str, str]]:
    """Return heterogeneous source-like records for Day 2 contract testing."""
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


def normalize_source_records(records: list[dict[str, str]]) -> list[NewsItem]:
    """Map heterogeneous records into the shared NewsItem schema."""
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


def fetch_stub_items() -> list[NewsItem]:
    """Backwards-compatible helper used by tests and workflow."""
    return normalize_source_records(fetch_stub_source_records())


def fetch_contract_stub_items() -> list[NewsItem]:
    """Alias with Day 2 naming for clarity in new code."""
    return [
        *fetch_stub_items(),
    ]
