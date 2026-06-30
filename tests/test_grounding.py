"""Tests for the source-grounding guard.

Real data, no mocks: roots are derived from the committed preflight
``requires_web_fetch`` list, and the published 6/30 digest is asserted clean so
a regression that reintroduces fabricated leaderboard-root links fails the suite.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from pipeline.grounding import (
    collect_roots,
    find_ungrounded,
    is_ungrounded,
    normalize_url,
    strip_ungrounded,
)

ROOT = Path(__file__).resolve().parent.parent
PREFLIGHT = ROOT / ".preflight" / "preflight_20260630120000.json"
REPORT = ROOT / "reports" / "20260630120000.json"

_PREFLIGHT_DATA = json.loads(PREFLIGHT.read_text(encoding="utf-8"))
ROOTS = collect_roots(_PREFLIGHT_DATA.get("requires_web_fetch"))


class Normalize(unittest.TestCase):
    def test_scheme_www_query_and_trailing_slash_dropped(self) -> None:
        self.assertEqual(
            normalize_url("https://www.Vellum.ai/llm-leaderboard/"),
            "vellum.ai/llm-leaderboard",
        )
        self.assertEqual(
            normalize_url("http://youtube.com/watch?v=x&t=12s"), "youtube.com/watch"
        )


class Roots(unittest.TestCase):
    def test_real_preflight_roots_present(self) -> None:
        for expected in (
            "artificialanalysis.ai/leaderboards/models",
            "artificialanalysis.ai/image/leaderboard/text-to-image",
            "arena.ai/leaderboard/text-to-image",
            "vellum.ai/llm-leaderboard",
            "vellum.ai/open-llm-leaderboard",
        ):
            self.assertIn(expected, ROOTS)

    def test_structured_endpoints_included(self) -> None:
        self.assertIn("evalplus.github.io/results.json", ROOTS)


class IsUngrounded(unittest.TestCase):
    def test_leaderboard_root_is_ungrounded(self) -> None:
        self.assertTrue(is_ungrounded("https://arena.ai/leaderboard/text-to-image", ROOTS))

    def test_bare_domain_is_ungrounded(self) -> None:
        self.assertTrue(is_ungrounded("https://example.com", ROOTS))
        self.assertTrue(is_ungrounded("", ROOTS))

    def test_real_article_urls_are_grounded(self) -> None:
        for url in (
            "https://artificialanalysis.ai/models/claude-fable-5",
            "https://typographica.org/typeface-reviews/lava-devanagari-kannada-and-telugu/",
            "https://www.youtube.com/watch?v=7c_ieWfAbrw&t=2420s",
            "https://www.figure.ai/blog/one-robot-per-hour-botq",
        ):
            self.assertFalse(is_ungrounded(url, ROOTS), url)


class Strip(unittest.TestCase):
    def _categories(self) -> list[dict]:
        return [
            {
                "id": "leaderboard",
                "stories": [{"title": "ok", "url": "https://artificialanalysis.ai/leaderboards/models"}],
            },
            {
                "id": "image-gen",
                "stories": [
                    {"title": "fab", "source": "Arena AI Benchmark Suite", "url": "https://arena.ai/leaderboard/text-to-image"},
                ],
            },
            {
                "id": "robotics",
                "stories": [
                    {"title": "real", "source": "Figure AI", "url": "https://www.figure.ai/blog/x"},
                    {"title": "fab", "source": "Vellum Index", "url": "https://www.vellum.ai/llm-leaderboard"},
                ],
            },
        ]

    def test_leaderboard_root_exempt_and_gap_root_dropped(self) -> None:
        kept, dropped = strip_ungrounded(self._categories(), ROOTS)
        ids = {c["id"] for c in kept}
        self.assertIn("leaderboard", ids)   # exempt: root link allowed
        self.assertNotIn("image-gen", ids)  # only story dropped -> empty -> removed
        self.assertEqual(len(dropped), 2)

    def test_real_story_survives_in_mixed_category(self) -> None:
        kept, _ = strip_ungrounded(self._categories(), ROOTS)
        robotics = next(c for c in kept if c["id"] == "robotics")
        self.assertEqual([s["title"] for s in robotics["stories"]], ["real"])


class PublishedDigestClean(unittest.TestCase):
    def test_no_ungrounded_stories_in_660_report(self) -> None:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        offenders = find_ungrounded(data.get("categories") or [], ROOTS)
        self.assertEqual(offenders, [], f"ungrounded stories remain: {offenders}")


if __name__ == "__main__":
    unittest.main()
