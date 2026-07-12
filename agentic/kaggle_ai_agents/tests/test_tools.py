from kaggle_ai_agents.tools.news_sources import fetch_stub_items


def test_fetch_stub_items_returns_items() -> None:
    items = fetch_stub_items()
    assert len(items) >= 1
    assert items[0].title
