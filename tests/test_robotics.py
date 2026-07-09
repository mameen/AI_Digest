"""Robotics feed fetcher: parse real RSS fixtures into grounded story cards.

No mocks. The three feeds (The Robot Report, IEEE Spectrum Robotics, Robohub)
are captured live and trimmed to 2 items each under ``tests/data/``; the actual
production parser runs against them. The only I/O seam (``fetch``) is
dependency-injected so ``fetch_stories`` runs fully offline against the fixtures.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from llm_pipeline.paths import VENDOR_DIR

_SCRIPTS = VENDOR_DIR / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fetch_robotics_news import (  # noqa: E402
    SOURCES,
    fetch_stories,
    parse_feed,
    to_story_cards,
)

_DATA = Path(__file__).parent / "data"
_FIXTURES = {
    "The Robot Report":       "robotics_therobotreport_rss.xml",
    "IEEE Spectrum Robotics": "robotics_ieee_spectrum_rss.xml",
    "Robohub":                "robotics_robohub_rss.xml",
}
# First article URL in each trimmed fixture (ASCII — stable to assert on).
_FIRST_URL = {
    "The Robot Report":       "https://www.therobotreport.com/in-robotics-ruggedization-is-no-longer-optional/",
    "IEEE Spectrum Robotics": "https://spectrum.ieee.org/video-friday-robot-grippers",
    "Robohub":                "https://robohub.org/whats-coming-up-at-robocup2026/",
}


def _feed(source: str) -> bytes:
    return (_DATA / _FIXTURES[source]).read_bytes()


class ParseFeed(unittest.TestCase):
    def test_each_fixture_parses_two_articles(self) -> None:
        for source in _FIXTURES:
            arts = parse_feed(_feed(source), source)
            self.assertEqual(len(arts), 2, source)
            self.assertEqual(arts[0]["source"], source)
            self.assertEqual(arts[0]["url"], _FIRST_URL[source])
            self.assertTrue(arts[0]["title"])

    def test_limit_caps_articles(self) -> None:
        arts = parse_feed(_feed("The Robot Report"), "The Robot Report", limit=1)
        self.assertEqual(len(arts), 1)

    def test_atom_feed_parses(self) -> None:
        atom = (
            b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">'
            b"<entry><title>Embodied AI demo</title>"
            b'<link href="https://example.org/robot-a"/></entry></feed>'
        )
        arts = parse_feed(atom, "Atom Source")
        self.assertEqual(arts, [
            {
                "source": "Atom Source",
                "title": "Embodied AI demo",
                "url": "https://example.org/robot-a",
                "body_html": "",
            }
        ])


class ToStoryCards(unittest.TestCase):
    def test_dedupes_and_tags(self) -> None:
        raw = {src: parse_feed(_feed(src), src) for src in _FIXTURES}
        cards = to_story_cards(raw)
        self.assertEqual(len(cards), 6)  # 3 sources x 2, all distinct urls
        self.assertEqual(len({c["url"] for c in cards}), 6)
        for c in cards:
            self.assertIn("robotics", c["tags"])
            self.assertIn("embodied-ai", c["tags"])
            self.assertEqual(c["summary"], "")  # unscored — Claude/LLM fills

    def test_rss_body_embedded_links(self) -> None:
        raw = {"The Robot Report": parse_feed(_feed("The Robot Report"), "The Robot Report")}
        cards = to_story_cards(raw)
        rugged = next(c for c in cards if "Ruggedization" in c["title"])
        urls = {l["url"] for l in rugged.get("links") or []}
        self.assertTrue(any("wibotic.com" in u for u in urls))

    def test_errors_are_skipped(self) -> None:
        raw = {
            "Good": parse_feed(_feed("The Robot Report"), "The Robot Report"),
            "Bad": [{"error": "boom", "source": "Bad"}],
        }
        cards = to_story_cards(raw)
        self.assertEqual(len(cards), 2)


class FetchStories(unittest.TestCase):
    def test_offline_via_injected_fetch(self) -> None:
        url_to_source = {url: src for src, (url, _lim) in SOURCES.items()}

        def fake_fetch(url: str) -> bytes:
            return _feed(url_to_source[url])

        cat = fetch_stories(fetch=fake_fetch)
        self.assertEqual(cat["id"], "robotics")
        self.assertEqual(cat["icon"], "🤖")
        self.assertEqual(len(cat["stories"]), 6)

    def test_one_dead_source_does_not_sink_the_rest(self) -> None:
        url_to_source = {url: src for src, (url, _lim) in SOURCES.items()}
        dead = SOURCES["Robohub"][0]

        def flaky_fetch(url: str) -> bytes:
            if url == dead:
                raise RuntimeError("feed 500")
            return _feed(url_to_source[url])

        cat = fetch_stories(fetch=flaky_fetch)
        self.assertEqual(len(cat["stories"]), 4)  # two live sources survive


if __name__ == "__main__":
    unittest.main()
