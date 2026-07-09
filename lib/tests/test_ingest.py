"""Tests for lib.ingest — fixture-backed, no mocks."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.ingest import aisearch, leaderboard  # noqa: E402
from lib.ingest.bundle import clear_bundle_cache  # noqa: E402
from lib.ingest.dispatch import research_topic  # noqa: E402
from lib.ingest.markdown import bullets_to_markdown  # noqa: E402
from lib.ingest.types import IngestBundle  # noqa: E402


class AisearchIngestTest(unittest.TestCase):
    def test_bullets_from_preflight_fixture(self) -> None:
        fixture = json.loads(
            (ROOT / "tests/data/preflight_20260630120000.json").read_text(encoding="utf-8")
        )
        fixture["categories"] = [
            {
                "id": "aisearch",
                "_video_url": "https://www.youtube.com/watch?v=abc123",
                "_video_title": "Demo episode",
                "stories": [
                    {"title": "Intro", "url": "https://www.youtube.com/watch?v=abc123&t=0s"},
                    {"title": "Topic A", "url": "https://www.youtube.com/watch?v=abc123&t=60s"},
                    {"title": "Topic B", "url": "https://www.youtube.com/watch?v=abc123&t=120s"},
                ],
            }
        ]
        bullets = aisearch.bullets_from_preflight(fixture)
        self.assertGreaterEqual(len(bullets), 3)
        md = bullets_to_markdown("aisearch", bullets)
        self.assertIn("Intro", md)
        self.assertIn("youtube.com", md)


class LeaderboardIngestTest(unittest.TestCase):
    def test_bullets_from_fixture_crawl_and_structured(self) -> None:
        bundle = IngestBundle(
            prefix="20260706150100",
            preflight_path=ROOT / "tests/data/preflight_20260630120000.json",
            preflight={"categories": []},
            crawl_paths=[ROOT / "tests/data/artificialanalysis.ai_leaderboards_models.md"],
            structured_paths=[
                ROOT / "tests/data/swebench_leaderboards.json",
                ROOT / "tests/data/evalplus_results.json",
            ],
        )
        result = leaderboard.research({}, bundle)
        self.assertGreaterEqual(len(result.bullets), 3)
        self.assertEqual(result.seed, leaderboard.SEED)
        titles = " ".join(b.title for b in result.bullets)
        self.assertIn("AA Intelligence", titles)
        self.assertIn("SWE-bench", titles)
        self.assertIn("EvalPlus", titles)


class DispatchIngestTest(unittest.TestCase):
    def test_research_topic_uses_bundle_cache(self) -> None:
        clear_bundle_cache()
        prefix = "20260706150200"
        import lib.ingest.bundle as bundle_mod

        fixture = {
            "categories": [
                {
                    "id": "aisearch",
                    "stories": [
                        {"title": "A", "url": "https://example.com/a/1"},
                        {"title": "B", "url": "https://example.com/b/2"},
                        {"title": "C", "url": "https://example.com/c/3"},
                    ],
                }
            ]
        }
        bundle_mod._CACHE[prefix] = IngestBundle(
            prefix=prefix,
            preflight_path=ROOT / "tests/data/preflight_20260630120000.json",
            preflight=fixture,
        )
        try:
            result = research_topic({}, prefix, "aisearch")
            self.assertEqual(result.topic, "aisearch")
            self.assertGreaterEqual(len(result.bullets), 3)
        finally:
            clear_bundle_cache()


if __name__ == "__main__":
    unittest.main()
