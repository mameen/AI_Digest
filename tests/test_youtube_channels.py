"""Multi-channel YouTube ingest (wide net, fixture-backed)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from llm_pipeline.paths import VENDOR_DIR

_SCRIPTS = VENDOR_DIR / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from link_extract import parse_description_resources
from youtube_channels import (  # noqa: E402
    SECONDARY_CHANNELS,
    attach_story_links,
    chapter_url,
    extract_topics,
    fetch_youtube_secondary_category,
    is_members_only_error,
    match_resources_to_topics,
    parse_description_timestamps,
    topics_to_story_cards,
)

_STACK_DESC = (
    Path(__file__).parent / "data" / "the_stack_tools_sample.txt"
).read_text(encoding="utf-8").strip()

_DATA = Path(__file__).parent / "data"
_DESC = (_DATA / "theaisearch_description_sample.txt").read_text(encoding="utf-8").strip()


class TimestampParser(unittest.TestCase):
    def test_parses_mm_ss_and_hms_lines(self) -> None:
        topics = parse_description_timestamps(
            "00:00 dSpark intro\n01:05 Deepseek situation\n1:02:20 Results\n"
        )
        self.assertEqual([t["title"] for t in topics], ["dSpark intro", "Deepseek situation", "Results"])
        self.assertEqual(topics[0]["start_s"], 0)
        self.assertEqual(topics[1]["start_s"], 65)
        self.assertEqual(topics[2]["start_s"], 3740)

    def test_real_fixture_has_multiple_topics(self) -> None:
        topics = parse_description_timestamps(_DESC)
        self.assertGreaterEqual(len(topics), 3)
        self.assertTrue(any("dSpark" in t["title"] for t in topics))


class TopicExtraction(unittest.TestCase):
    def test_prefers_chapters_over_description(self) -> None:
        info = {
            "url": "https://www.youtube.com/watch?v=abc",
            "title": "Episode",
            "description": "00:00 from description only",
            "chapters": [{"title": "Real chapter", "start_time": 30}],
        }
        topics = extract_topics(info)
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]["title"], "Real chapter")
        self.assertEqual(topics[0]["origin"], "chapter")

    def test_falls_back_to_description_timestamps(self) -> None:
        info = {
            "url": "https://www.youtube.com/watch?v=abc",
            "title": "Episode",
            "description": _DESC,
            "chapters": [],
        }
        topics = extract_topics(info)
        self.assertGreater(len(topics), 1)
        self.assertEqual(topics[0]["origin"], "description")

    def test_whole_video_when_no_chapters_or_timestamps(self) -> None:
        topics = extract_topics(
            {"url": "https://www.youtube.com/watch?v=x", "title": "Solo", "description": "no timestamps"}
        )
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0]["origin"], "video")


class ResourceLinks(unittest.TestCase):
    def test_parses_tools_section(self) -> None:
        resources = parse_description_resources(_STACK_DESC)
        names = {r["name"] for r in resources}
        self.assertIn("Aider", names)
        self.assertIn("OpenCode", names)
        self.assertTrue(any("gemini" in n.lower() for n in names))

    def test_maps_tools_to_chapters(self) -> None:
        topics = parse_description_timestamps(_STACK_DESC)
        resources = parse_description_resources(_STACK_DESC)
        mapping = match_resources_to_topics(topics, resources, _STACK_DESC)
        self.assertTrue(mapping["Free Frontier Models, No Card Required"])
        self.assertTrue(any("gemini" in l["name"].lower() for l in mapping["Free Frontier Models, No Card Required"]))
        self.assertTrue(mapping["Auto-Commits Every AI Edit to Git"])
        self.assertTrue(any("aider" in l["name"].lower() for l in mapping["Auto-Commits Every AI Edit to Git"]))

    def test_attach_story_links_on_cards(self) -> None:
        info = {
            "url": "https://www.youtube.com/watch?v=SFOVWPAhJtk",
            "title": "6 FREE Tools That Replace Claude Code (And Beat It)",
            "description": _STACK_DESC,
            "chapters": [
                {"title": "Free Frontier Models, No Card Required", "start_time": 21},
                {"title": "Auto-Commits Every AI Edit to Git", "start_time": 327},
            ],
        }
        _topics, stories = topics_to_story_cards(
            info, channel_key="the-stack-ai", channel_label="The Stack"
        )
        by_title = {s["title"]: s for s in stories}
        frontier = by_title["Free Frontier Models, No Card Required"]
        commits = by_title["Auto-Commits Every AI Edit to Git"]
        self.assertEqual(len(frontier["links"]), 4)
        self.assertEqual(len(commits["links"]), 4)
        self.assertIn("gemini", frontier["links"][0]["name"].lower())
        self.assertIn("aider", commits["links"][0]["name"].lower())


class StoryCards(unittest.TestCase):
    def test_channel_metadata_on_stories(self) -> None:
        info = {
            "url": "https://www.youtube.com/watch?v=abc",
            "title": "MCP vs API",
            "description": "",
            "chapters": [{"title": "How MCP works", "start_time": 120}],
        }
        topics, stories = topics_to_story_cards(
            info, channel_key="google-cloud-tech", channel_label="Google Cloud Tech"
        )
        self.assertEqual(len(stories), 1)
        self.assertEqual(stories[0]["channel_key"], "google-cloud-tech")
        self.assertEqual(stories[0]["source"], "Google Cloud Tech")
        self.assertEqual(stories[0]["topic"], "How MCP works")
        self.assertEqual(topics[0]["url"], chapter_url(info["url"], 120))


class MembersOnly(unittest.TestCase):
    def test_detects_members_only_errors(self) -> None:
        self.assertTrue(is_members_only_error(RuntimeError("Join this channel to get access to members-only content")))


class AggregateCategory(unittest.TestCase):
    def test_fetch_all_secondary_channels_with_fixtures(self) -> None:
        fixture = json.loads((_DATA / "youtube_channel_fixtures.json").read_text(encoding="utf-8"))
        import youtube_channels as yc
        from youtube_channels import build_channel_source

        def fake_fetch_channel_source(ch: dict[str, str], **kwargs: object) -> dict[str, object]:
            url = fixture["by_channel"][ch["key"]]
            info = dict(fixture[url])
            topics, stories = topics_to_story_cards(
                info, channel_key=ch["key"], channel_label=ch["label"]
            )
            src = build_channel_source(ch, info, topics)
            src["_stories"] = stories
            return src

        original = yc.fetch_channel_source
        yc.fetch_channel_source = fake_fetch_channel_source
        try:
            cat = fetch_youtube_secondary_category(max_workers=2)
        finally:
            yc.fetch_channel_source = original

        self.assertEqual(cat["id"], "youtube")
        self.assertEqual(len(cat["sources"]), len(SECONDARY_CHANNELS))
        self.assertGreater(len(cat["stories"]), len(SECONDARY_CHANNELS))
        self.assertEqual(
            {s["channel_key"] for s in cat["sources"]},
            {c["key"] for c in SECONDARY_CHANNELS},
        )


if __name__ == "__main__":
    unittest.main()
