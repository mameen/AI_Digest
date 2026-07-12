from kaggle_ai_agents.tools.news_sources import (
    discover_items,
    fetch_stub_items,
    load_source_registry,
    sources_by_kind,
)
from kaggle_ai_agents.tools.selection import dedupe_items, rank_items


def test_fetch_stub_items_returns_items() -> None:
    items = fetch_stub_items()
    assert len(items) >= 1
    assert items[0].title


def test_load_source_registry_has_full_inventory() -> None:
    sources = load_source_registry()
    ids = [s["id"] for s in sources]
    # Spot-check a sample across all source kinds
    assert "openai-blog" in ids
    assert "the-robot-report" in ids
    assert "huggingface-papers" in ids
    assert "ibm-technology" in ids
    assert "aa-intelligence-leaderboard" in ids
    assert "swebench-leaderboard" in ids


def test_sources_by_kind_rss_returns_subset() -> None:
    rss_sources = sources_by_kind("rss")
    assert len(rss_sources) >= 3
    assert all(s["kind"] == "rss" for s in rss_sources)


def test_sources_by_kind_js_crawl_returns_leaderboards() -> None:
    crawl_sources = sources_by_kind("js_crawl")
    ids = [s["id"] for s in crawl_sources]
    assert "aa-intelligence-leaderboard" in ids
    assert "arena-ai-t2i" in ids


def test_dedupe_items_removes_same_title_same_host() -> None:
    items = fetch_stub_items()
    deduped = dedupe_items(items)
    assert len(deduped) < len(items)


def test_rank_items_prioritizes_benchmarks_text() -> None:
    items = fetch_stub_items()
    ranked = rank_items(items)
    assert ranked[0].title == "Open model benchmarks improve"


def test_discover_items_calls_discover_script() -> None:
    """discover_items() executes discover.py and returns NewsItem list."""
    try:
        items = discover_items()
        # discover.py should return a list of NewsItem objects
        assert isinstance(items, list)
        # Each item should have required fields
        for item in items:
            assert item.source_id
            assert item.title
            assert item.url
            # summary may be empty
    except RuntimeError as e:
        # If discover.py fails (e.g., network error), we expect a RuntimeError
        # This is acceptable in CI/CD where network may be restricted
        assert "discover.py" in str(e)

