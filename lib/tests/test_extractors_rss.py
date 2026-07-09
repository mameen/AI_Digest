"""Tests for lib.ingest.extractors.rss — fixture feeds, no network."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.ingest.extractors.rss import FeedSpec, articles_to_bullets, parse_feed  # noqa: E402


class RssExtractorTest(unittest.TestCase):
    def test_parse_robotics_fixture(self) -> None:
        xml = (ROOT / "tests/data/robotics_therobotreport_rss.xml").read_bytes()
        articles = parse_feed(xml, "The Robot Report", limit=5)
        self.assertGreaterEqual(len(articles), 1)
        self.assertTrue(all("url" in a and "title" in a for a in articles))

    def test_articles_to_bullets(self) -> None:
        xml = (ROOT / "tests/data/robotics_robohub_rss.xml").read_bytes()
        articles = parse_feed(xml, "Robohub", limit=3)
        bullets = articles_to_bullets(articles, title_fmt="{source}: {title}")
        self.assertGreaterEqual(len(bullets), 1)
        self.assertIn("Robohub:", bullets[0].title)

    def test_feed_spec_labels_source_not_topic_module(self) -> None:
        spec = FeedSpec("IEEE Spectrum Robotics", "https://example.com/feed.rss")
        self.assertEqual(spec.label, "IEEE Spectrum Robotics")
        self.assertTrue(spec.url.endswith(".rss"))


if __name__ == "__main__":
    unittest.main()
