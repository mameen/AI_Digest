from kaggle_ai_agents.tools.news_sources import fetch_stub_items
from kaggle_ai_agents.tools.selection import dedupe_items, rank_items


def test_fetch_stub_items_returns_items() -> None:
    items = fetch_stub_items()
    assert len(items) >= 1
    assert items[0].title


def test_dedupe_items_removes_same_title_same_host() -> None:
    items = fetch_stub_items()
    deduped = dedupe_items(items)
    assert len(deduped) < len(items)


def test_rank_items_prioritizes_benchmarks_text() -> None:
    items = fetch_stub_items()
    ranked = rank_items(items)
    assert ranked[0].title == "Open model benchmarks improve"
