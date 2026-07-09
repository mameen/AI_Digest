"""Tests for lazy lib.ingest helpers — fixture-backed, no mocks."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.ingest.agent_tools import (  # noqa: E402
    fetch_rss,
    read_crawl_markdown_tool,
    read_preflight_category,
    read_structured_json_tool,
    read_topic_config,
)
from lib.ingest.bundle import clear_bundle_cache  # noqa: E402
from lib.ingest.dispatch import research_topic  # noqa: E402
from lib.ingest.lazy import ensure_preflight, materialize_binding_cache  # noqa: E402
from lib.ingest.topics.registry import binding_for  # noqa: E402


class LazyIngestTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_bundle_cache()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        self.prefix = "eval20260706160000"
        self.cfg = {
            "ingestion": {
                "force_refetch": False,
                "crawl4ai": {"enabled": False},
                "structured_sources": {"enabled": False},
            },
            "output": {
                "preflight_dir": str(self.tmp / "preflight"),
                "cache_dir": str(self.tmp / "cache"),
            },
        }

    def tearDown(self) -> None:
        self._tmpdir.cleanup()
        clear_bundle_cache()

    def test_read_topic_config_evaluation(self) -> None:
        result = read_topic_config("evaluation_test_topic")
        self.assertTrue(result["ok"])
        self.assertTrue(result["config"]["evaluation"])
        self.assertIn("preflight_category", result["config"]["kinds"])

    def test_lazy_preflight_seeds_from_evaluation_fixture(self) -> None:
        path = ensure_preflight(self.cfg, self.prefix, topic="evaluation_test_topic")
        self.assertTrue(path.is_file())
        data = json.loads(path.read_text(encoding="utf-8"))
        cats = [c["id"] for c in data.get("categories") or []]
        self.assertIn("evaluation_test_topic", cats)

    def test_read_preflight_category_from_eval_fixture(self) -> None:
        result = read_preflight_category(
            self.cfg,
            self.prefix,
            "evaluation_test_topic",
            topic="evaluation_test_topic",
        )
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(len(result["bullets"]), 3)

    def test_read_crawl_and_structured_from_eval_fixtures(self) -> None:
        crawl = read_crawl_markdown_tool(
            self.cfg,
            self.prefix,
            "artificialanalysis.ai_leaderboards_models.md",
            topic="evaluation_test_topic",
        )
        self.assertTrue(crawl["ok"], crawl)
        self.assertIn("markdown", crawl)

        swe = read_structured_json_tool(
            self.cfg,
            self.prefix,
            "swebench_leaderboards.json",
            topic="evaluation_test_topic",
        )
        self.assertTrue(swe["ok"], swe)
        self.assertIn("data", swe)

    def test_fetch_rss_eval_fixture_url(self) -> None:
        result = fetch_rss(
            [{"label": "Eval", "url": "eval:test_feed.xml", "limit": 3}],
        )
        self.assertTrue(result["ok"], result)
        self.assertGreaterEqual(len(result["articles"]), 1)

    def test_compose_evaluation_topic_without_network(self) -> None:
        binding = binding_for("evaluation_test_topic")
        assert binding is not None
        materialize_binding_cache(self.cfg, self.prefix, binding)
        result = research_topic(self.cfg, self.prefix, "evaluation_test_topic")
        self.assertEqual(result.topic, "evaluation_test_topic")
        self.assertGreaterEqual(len(result.bullets), 3)


if __name__ == "__main__":
    unittest.main()
