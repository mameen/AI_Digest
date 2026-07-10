"""Integration tests — Hermes wrappers delegate to lib.ingest."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERMES_PKG = ROOT / "agentic" / "hermes"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERMES_PKG) not in sys.path:
    sys.path.insert(0, str(HERMES_PKG))

import lib.ingest.bundle as bundle_mod  # noqa: E402
from lib.ingest.types import IngestBundle  # noqa: E402
from tools.artifacts import validate_researcher_artifact  # noqa: E402
from tools.researchers import aisearch, leaderboard, youtube  # noqa: E402
from tools.topics import load_demo_topics, research_category_ids  # noqa: E402


class DemoTopicsTest(unittest.TestCase):
    def test_demo_topics_derived_from_best_report(self) -> None:
        topics = load_demo_topics({"demo_topics": "auto"})
        self.assertGreaterEqual(len(topics), 11)
        self.assertIn("youtube", topics)
        self.assertEqual(
            research_category_ids({"demo_topics": "auto"}),
            frozenset(topics),
        )


class AisearchResearcherTest(unittest.TestCase):
    def test_seed_from_preflight_fixture(self) -> None:
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
        prefix = "20260706150000"
        bundle_mod._CACHE[prefix] = IngestBundle(
            prefix=prefix,
            preflight_path=ROOT / "tests/data/preflight_20260630120000.json",
            preflight=fixture,
        )
        try:
            with tempfile.TemporaryDirectory() as tmp:
                ws = Path(tmp)
                result = aisearch.seed("aisearch", ws, cfg={}, prefix=prefix)
                self.assertTrue(result.get("ok"), result)
                self.assertEqual(result.get("seed"), aisearch.SEED)
                self.assertEqual(validate_researcher_artifact(ws), [])
        finally:
            bundle_mod._CACHE.pop(prefix, None)


class LeaderboardResearcherTest(unittest.TestCase):
    def test_seed_from_crawl_and_structured_fixtures(self) -> None:
        prefix = "20260706150100"
        bundle_mod._CACHE[prefix] = IngestBundle(
            prefix=prefix,
            preflight_path=ROOT / "tests/data/preflight_20260630120000.json",
            preflight={"categories": []},
            crawl_paths=[ROOT / "tests/data/artificialanalysis.ai_leaderboards_models.md"],
            structured_paths=[
                ROOT / "tests/data/swebench_leaderboards.json",
                ROOT / "tests/data/evalplus_results.json",
            ],
        )
        try:
            with tempfile.TemporaryDirectory() as tmp:
                ws = Path(tmp)
                result = leaderboard.seed("leaderboard", ws, cfg={}, prefix=prefix)
                self.assertTrue(result.get("ok"), result)
                self.assertEqual(result.get("seed"), leaderboard.SEED)
                self.assertEqual(validate_researcher_artifact(ws), [])
        finally:
            bundle_mod._CACHE.pop(prefix, None)


class YoutubeResearcherTest(unittest.TestCase):
    def test_seed_from_youtube_preflight_fixture(self) -> None:
        fixture_path = ROOT / "tests/data/preflight_youtube_category.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        prefix = "20260709120000"
        bundle_mod._CACHE[prefix] = IngestBundle(
            prefix=prefix,
            preflight_path=fixture_path,
            preflight=fixture,
        )
        try:
            with tempfile.TemporaryDirectory() as tmp:
                ws = Path(tmp)
                result = youtube.seed("youtube", ws, cfg={}, prefix=prefix)
                self.assertTrue(result.get("ok"), result)
                self.assertEqual(result.get("seed"), youtube.SEED)
                self.assertEqual(validate_researcher_artifact(ws), [])
                text = (ws / "output.md").read_text(encoding="utf-8")
                self.assertIn("nate1", text)
                self.assertIn("ibm1", text)
        finally:
            bundle_mod._CACHE.pop(prefix, None)


if __name__ == "__main__":
    unittest.main()
