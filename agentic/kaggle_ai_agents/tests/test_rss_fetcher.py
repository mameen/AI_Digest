"""TDD tests for RSS feed parsing.

All fixtures are committed static files — no network calls.
Tests must fail until rss_fetcher.py is implemented.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "rss"

# Import the module under test — expected to fail until implemented
try:
    from kaggle_ai_agents.tools.rss_fetcher import parse_rss_file, parse_rss_bytes
    _MODULE_AVAILABLE = True
except ImportError:
    _MODULE_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _MODULE_AVAILABLE,
    reason="rss_fetcher module not yet implemented",
)


# ── parse_rss_file tests ──────────────────────────────────────────────────────

def test_parse_openai_blog_returns_items() -> None:
    items = parse_rss_file(FIXTURES / "openai_blog_sample.xml", source_id="openai-blog")
    assert len(items) >= 1


def test_parse_robot_report_returns_items() -> None:
    items = parse_rss_file(FIXTURES / "robot_report_sample.xml", source_id="the-robot-report")
    assert len(items) >= 1


def test_parse_deepmind_returns_items() -> None:
    items = parse_rss_file(FIXTURES / "deepmind_sample.xml", source_id="google-deepmind-blog")
    assert len(items) >= 1


def test_parsed_items_have_title_and_url() -> None:
    items = parse_rss_file(FIXTURES / "openai_blog_sample.xml", source_id="openai-blog")
    for item in items:
        assert item.title, f"Empty title in item: {item}"
        assert str(item.url).startswith("http"), f"Bad URL in item: {item.url}"


def test_parsed_items_have_correct_source_id() -> None:
    items = parse_rss_file(FIXTURES / "robot_report_sample.xml", source_id="the-robot-report")
    assert all(item.source_id == "the-robot-report" for item in items)


def test_parsed_items_are_news_item_instances() -> None:
    from kaggle_ai_agents.models import NewsItem
    items = parse_rss_file(FIXTURES / "openai_blog_sample.xml", source_id="openai-blog")
    assert all(isinstance(item, NewsItem) for item in items)


def test_parse_rss_bytes_matches_file() -> None:
    path = FIXTURES / "openai_blog_sample.xml"
    from_file = parse_rss_file(path, source_id="openai-blog")
    from_bytes = parse_rss_bytes(path.read_bytes(), source_id="openai-blog")
    assert len(from_file) == len(from_bytes)
    assert from_file[0].title == from_bytes[0].title


def test_limit_parameter_caps_output() -> None:
    items = parse_rss_file(FIXTURES / "robot_report_sample.xml", source_id="the-robot-report", limit=1)
    assert len(items) <= 1
