"""Tests for board topic resolution from best known-good report."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERMES_PKG = ROOT / "agentic" / "hermes"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERMES_PKG) not in sys.path:
    sys.path.insert(0, str(HERMES_PKG))

from tools.topics import (  # noqa: E402
    _category_ids_from_digest,
    _goodness_from_errors,
    _report_json_paths,
    best_known_good_report,
    load_demo_topics,
    resolve_board_topics,
)
from llm_pipeline.validate import validate_digest  # noqa: E402


class BoardTopicsTest(unittest.TestCase):
    def test_best_report_is_richest_passing_run(self) -> None:
        best = best_known_good_report()
        self.assertIsNotNone(best)
        assert best is not None
        self.assertGreaterEqual(best["story_total"], 40)
        self.assertGreater(best["category_count"], 0)
        # Richest among all passing reports on disk.
        from tools.baseline import agentic_config, validation_roots

        cfg = agentic_config()
        richest: tuple[int, str] | None = None
        for path in _report_json_paths():
            try:
                digest = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            pfx = str(digest.get("filename_prefix") or path.stem)
            errors = validate_digest(cfg, digest, validation_roots(cfg, pfx))
            if _goodness_from_errors(errors) == "fail":
                continue
            total = sum(len(c.get("stories") or []) for c in digest.get("categories") or [])
            if total <= 0:
                continue
            if richest is None or total > richest[0]:
                richest = (total, pfx)
        assert richest is not None
        self.assertEqual(best["prefix"], richest[1])
        self.assertEqual(best["story_total"], richest[0])

    def test_auto_topics_match_full_category_list(self) -> None:
        best = best_known_good_report()
        self.assertIsNotNone(best)
        assert best is not None
        board = resolve_board_topics({"demo_topics": "auto"})
        self.assertEqual(board["source"], "best_known_good_report")
        self.assertEqual(board["source_prefix"], best["prefix"])
        topics = board["topics"]
        self.assertEqual(topics, best["topics"])
        self.assertIn("youtube", topics)
        self.assertIn("aisearch", topics)
        self.assertGreaterEqual(len(topics), 11)

    def test_load_demo_topics_auto_from_yaml(self) -> None:
        topics = load_demo_topics()
        self.assertGreaterEqual(len(topics), 11)
        self.assertIn("analytics", topics)

    def test_explicit_override_wins(self) -> None:
        board = resolve_board_topics({"demo_topics": ["evaluation_test_topic"]})
        self.assertEqual(board["topics"], ["evaluation_test_topic"])
        self.assertEqual(board["source"], "hermes_roles.yaml")

    def test_category_ids_canonical_order(self) -> None:
        best = best_known_good_report()
        assert best is not None
        ids = _category_ids_from_digest(best["digest"])
        self.assertEqual(ids[0], "leaderboard")
        self.assertEqual(ids[-1], "research")


if __name__ == "__main__":
    unittest.main()
