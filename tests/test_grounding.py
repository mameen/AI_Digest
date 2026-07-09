"""Tests for the source-grounding guard.

Real data, no mocks: roots are derived from the committed preflight
fixture under ``tests/data/`` (or a local ``.preflight/`` copy when present),
and the published 6/30 digest is asserted clean so
"""

from __future__ import annotations

import json
import unittest

from lib.paths import LLM_PIPELINE_ROOT, REPO_ROOT
from pipeline.grounding import (
    annotate_ungrounded,
    collect_ingestion_urls,
    collect_roots,
    collect_skeleton_urls,
    find_ungrounded,
    is_ungrounded,
    normalize_url,
    strip_ungrounded,
)

ROOT = REPO_ROOT
PREFLIGHT_FIXTURE = ROOT / "tests" / "data" / "preflight_20260630120000.json"
PREFLIGHT_LOCAL = LLM_PIPELINE_ROOT / ".preflight" / "preflight_20260630120000.json"
REPORT = LLM_PIPELINE_ROOT / "reports" / "20260630120000.json"

_PREFLIGHT_PATH = PREFLIGHT_LOCAL if PREFLIGHT_LOCAL.is_file() else PREFLIGHT_FIXTURE
_PREFLIGHT_DATA = json.loads(_PREFLIGHT_PATH.read_text(encoding="utf-8"))
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


class IngestionAllowSet(unittest.TestCase):
    """In-context check: a URL the model was never shown is ungrounded."""

    INGESTION = (
        "## Crawl: figure.md\n"
        "Figure announced production ramp — see https://www.figure.ai/news/project-go-big.\n"
        "Also [BMW deal](https://figure.ai/news/f-03-at-bmw) and a trailing ref "
        "(https://artificialanalysis.ai/models/mercury-2).\n"
    )

    def test_collect_extracts_and_normalizes(self) -> None:
        urls = collect_ingestion_urls(self.INGESTION)
        self.assertIn("figure.ai/news/project-go-big", urls)
        self.assertIn("figure.ai/news/f-03-at-bmw", urls)  # markdown-link paren trimmed
        self.assertIn("artificialanalysis.ai/models/mercury-2", urls)  # trailing ) trimmed

    def test_fabricated_deep_path_is_ungrounded_in_context(self) -> None:
        allow = collect_ingestion_urls(self.INGESTION)
        # The 404 /blog/ path the root-only check can't catch:
        self.assertFalse(is_ungrounded("https://www.figure.ai/blog/project-go-big", ROOTS))
        self.assertTrue(
            is_ungrounded("https://www.figure.ai/blog/project-go-big", ROOTS, allow_urls=allow)
        )

    def test_shown_url_is_grounded_in_context(self) -> None:
        allow = collect_ingestion_urls(self.INGESTION)
        self.assertFalse(
            is_ungrounded("https://figure.ai/news/project-go-big", ROOTS, allow_urls=allow)
        )


class SkeletonAllowSet(unittest.TestCase):
    """Curated-feed URLs must count as grounded, even when absent from crawls."""

    def test_real_preflight_feed_urls_collected(self) -> None:
        urls = collect_skeleton_urls(_PREFLIGHT_DATA)
        # Curated categories (aisearch/typography/research) carry these links in
        # their per-category feeds, not the shared crawl ingestion string.
        self.assertTrue(any(u.startswith("youtube.com/watch") for u in urls))
        self.assertTrue(any("ilovetypography.com" in u for u in urls))
        self.assertTrue(any("huggingface.co/papers" in u for u in urls))

    def test_curated_link_grounded_via_skeleton_not_crawl(self) -> None:
        crawl_only = collect_ingestion_urls("## Crawl: x\nNothing relevant here.\n")
        allow = crawl_only | collect_skeleton_urls(_PREFLIGHT_DATA)
        url = "https://www.youtube.com/watch?v=7c_ieWfAbrw&t=2420s"
        self.assertTrue(is_ungrounded(url, ROOTS, allow_urls=crawl_only))  # crawl alone misses it
        self.assertFalse(is_ungrounded(url, ROOTS, allow_urls=allow))  # skeleton rescues it


class Annotate(unittest.TestCase):
    """Keep-the-topic policy: demote the link, never drop the story."""

    def _categories(self) -> list[dict]:
        return [
            {"id": "leaderboard", "stories": [{"title": "ok", "url": "https://arena.ai/leaderboard/text-to-image"}]},
            {
                "id": "robotics",
                "stories": [
                    {"title": "real", "source": "Figure AI", "url": "https://www.figure.ai/news/project-go-big"},
                    {"title": "fab", "source": "Figure AI", "url": "https://www.figure.ai/blog/invented"},
                ],
            },
        ]

    def test_topic_kept_and_link_demoted(self) -> None:
        allow = {"figure.ai/news/project-go-big"}
        kept, demoted = annotate_ungrounded(self._categories(), ROOTS, ingestion_urls=allow)
        robotics = next(c for c in kept if c["id"] == "robotics")
        # Both stories survive — no topic lost.
        self.assertEqual([s["title"] for s in robotics["stories"]], ["real", "fab"])
        real, fab = robotics["stories"]
        self.assertEqual(real["url"], "https://www.figure.ai/news/project-go-big")
        self.assertFalse(real.get("source_pending"))
        self.assertIsNone(fab["url"])
        self.assertTrue(fab["source_pending"])
        self.assertEqual([d["title"] for d in demoted], ["fab"])

    def test_leaderboard_root_exempt(self) -> None:
        kept, _ = annotate_ungrounded(self._categories(), ROOTS)
        lb = next(c for c in kept if c["id"] == "leaderboard")
        self.assertEqual(lb["stories"][0]["url"], "https://arena.ai/leaderboard/text-to-image")


class FindUngrounded(unittest.TestCase):
    def test_demoted_story_is_not_an_offender(self) -> None:
        # A guard-demoted story (url cleared, source_pending) shows no link, so
        # validation must not flag it; only a live ungrounded URL is an offender.
        cats = [
            {
                "id": "robotics",
                "stories": [
                    {"title": "kept", "source": "Figure AI", "url": None, "source_pending": True},
                    {"title": "bad", "source": "X", "url": "https://arena.ai/leaderboard/text-to-image"},
                ],
            }
        ]
        offenders = find_ungrounded(cats, ROOTS)
        self.assertEqual([o["title"] for o in offenders], ["bad"])


class PublishedDigestClean(unittest.TestCase):
    def test_no_ungrounded_stories_in_660_report(self) -> None:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        offenders = find_ungrounded(data.get("categories") or [], ROOTS)
        self.assertEqual(offenders, [], f"ungrounded stories remain: {offenders}")


if __name__ == "__main__":
    unittest.main()
