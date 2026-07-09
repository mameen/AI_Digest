"""Tests for shared link extraction (GitHub, X, LinkedIn, announcements)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from llm_pipeline.paths import VENDOR_DIR

_SCRIPTS = VENDOR_DIR / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from link_extract import (  # noqa: E402
    attach_story_embedded_links,
    classify_url,
    extract_links_from_text,
    html_embedded_text,
    parse_description_resources,
)

_AISEARCH = (
    Path(__file__).parent / "data" / "theaisearch_description_sample.txt"
).read_text(encoding="utf-8")
_STACK = (
    Path(__file__).parent / "data" / "the_stack_tools_sample.txt"
).read_text(encoding="utf-8")


class LinkExtract(unittest.TestCase):
    def test_classify_github_x_linkedin(self) -> None:
        self.assertEqual(classify_url("https://github.com/org/repo"), "github")
        self.assertEqual(classify_url("https://x.com/user/status/1"), "x")
        self.assertEqual(classify_url("https://www.linkedin.com/posts/foo"), "linkedin")

    def test_html_anchor_becomes_named_url(self) -> None:
        html = '<p>Repo <a href="https://github.com/org/repo">org/repo</a></p>'
        text = html_embedded_text(html)
        links = extract_links_from_text(text, allow_named_product_urls=True)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["kind"], "github")

    def test_attach_story_embedded_links_from_summary(self) -> None:
        story = {
            "url": "https://example.com/article",
            "title": "Demo",
            "summary": "See https://github.com/foo/bar for code.",
        }
        attach_story_embedded_links(story)
        self.assertEqual(story["links"][0]["kind"], "github")

        line = "- OpenCode: https://opencode.ai"
        links = extract_links_from_text(line, allow_named_product_urls=True)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["name"], "OpenCode")
        self.assertEqual(links[0]["url"], "https://opencode.ai")

    def test_aisearch_named_lines_with_allow(self) -> None:
        links = extract_links_from_text(_AISEARCH, allow_named_product_urls=True)
        kinds = {l["kind"] for l in links}
        self.assertIn("github", kinds)
        self.assertIn("huggingface", kinds)

    def test_stack_tools_section(self) -> None:
        tools = parse_description_resources(_STACK)
        self.assertEqual(len(tools), 4)
        self.assertEqual({t["name"] for t in tools}, {"Aider", "OpenCode", "Gemini CLI", "cc-switch"})

    def test_skips_youtube_watch_links(self) -> None:
        text = "Watch https://www.youtube.com/watch?v=abc and repo https://github.com/a/a"
        links = extract_links_from_text(text)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["kind"], "github")


if __name__ == "__main__":
    unittest.main()
