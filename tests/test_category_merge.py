"""Fixture-backed tests for category merge and baseline carry-forward."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERMES = ROOT / "agentic" / "hermes"
if str(HERMES) not in sys.path:
    sys.path.insert(0, str(HERMES))

_merge_spec = importlib.util.spec_from_file_location(
    "category_merge", HERMES / "tools" / "category_merge.py"
)
assert _merge_spec and _merge_spec.loader
category_merge = importlib.util.module_from_spec(_merge_spec)
_merge_spec.loader.exec_module(category_merge)

_show_spec = importlib.util.spec_from_file_location("showcase", HERMES / "tools" / "showcase.py")
assert _show_spec and _show_spec.loader
showcase = importlib.util.module_from_spec(_show_spec)
_show_spec.loader.exec_module(showcase)

BASELINE_PATH = ROOT / "llm_pipeline" / "reports" / "20260703120000.json"


class MergeStoriesByUrlTest(unittest.TestCase):
    def test_fresh_first_keeps_non_overlapping_baseline(self) -> None:
        baseline = [
            {"title": "Old A", "url": "https://example.com/a", "provenance": "carry:agentic:base"},
            {"title": "Old B", "url": "https://example.com/b", "provenance": "carry:agentic:base"},
        ]
        fresh = [
            {"title": "New B", "url": "https://example.com/b", "provenance": "agent:synthesizer:aisearch"},
        ]
        merged = category_merge.merge_stories_by_url(baseline, fresh)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["title"], "New B")
        self.assertEqual(merged[1]["title"], "Old A")

    def test_youtube_baseline_survives_when_only_leaderboard_synthesized(self) -> None:
        if not BASELINE_PATH.is_file():
            self.skipTest("baseline fixture missing")
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        yt_before = next(c for c in baseline["categories"] if c["id"] == "youtube")
        self.assertGreater(len(yt_before.get("stories") or []), 0)

        cat_by_id = {c["id"]: copy.deepcopy(c) for c in baseline["categories"]}
        grouped = {
            "leaderboard": [
                {
                    "title": "Fresh LB",
                    "url": "https://example.com/lb-new",
                    "provenance": "agent:synthesizer:leaderboard",
                }
            ]
        }
        for cid, fresh in grouped.items():
            existing = (cat_by_id.get(cid) or {}).get("stories") or []
            cat_by_id[cid] = {
                **cat_by_id.get(cid, {"id": cid}),
                "stories": category_merge.merge_stories_by_url(existing, fresh),
            }

        yt_after = cat_by_id["youtube"]
        self.assertEqual(len(yt_after["stories"]), len(yt_before["stories"]))


class BaselineDigestTest(unittest.TestCase):
    def test_pinned_baseline_includes_youtube_stories(self) -> None:
        from tools.baseline import agentic_config

        digest = showcase.load_baseline_digest(agentic_config())
        yt = next((c for c in digest.get("categories") or [] if c.get("id") == "youtube"), None)
        self.assertIsNotNone(yt, "baseline must include youtube category")
        self.assertGreater(len(yt.get("stories") or []), 0)


if __name__ == "__main__":
    unittest.main()
