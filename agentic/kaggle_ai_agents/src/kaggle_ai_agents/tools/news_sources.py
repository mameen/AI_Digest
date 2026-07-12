"""Deterministic source adapter stubs used for local testing."""

from __future__ import annotations

from kaggle_ai_agents.models import NewsItem


def fetch_stub_items() -> list[NewsItem]:
    return [
        NewsItem(
            source_id="demo",
            title="Open model benchmarks improve",
            url="https://example.com/open-model-benchmarks",
            summary="New results show quality gains with lower latency.",
        ),
        NewsItem(
            source_id="demo",
            title="Agent tooling standards emerging",
            url="https://example.com/agent-tooling-standards",
            summary="Interoperability efforts reduce integration friction.",
        ),
    ]
