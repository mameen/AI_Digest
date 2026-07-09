"""theAIsearch RSS fetch: retry/backoff over a real feed fixture, no mocks.

The only I/O seams (``fetch`` and ``sleep``) are dependency-injected, so the
retry driver runs against a committed Atom feed fixture and scripted transient
failures exactly as it would against the live, occasionally-throttled YouTube
feed endpoint.

The fixture is a schema-faithful, 2-entry trim of a real theAIsearch channel
feed (captured live earlier); it was hand-trimmed rather than re-captured at
test-authoring time because YouTube was actively throttling the feed endpoint.
"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
from pathlib import Path

from llm_pipeline.paths import VENDOR_DIR

_SCRIPTS = VENDOR_DIR / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from fetch_video_chapters import (  # noqa: E402
    _parse_latest,
    _parse_ytdlp_flat,
    attach_video_metadata,
    get_latest_video_url,
)

_DATA = Path(__file__).parent / "data"
_RSS_FIXTURE = _DATA / "theaisearch_rss.xml"
_YTDLP_FIXTURE = _DATA / "theaisearch_ytdlp_flat.json"
_FEED = _RSS_FIXTURE.read_bytes()
_YTDLP_FLAT = json.loads(_YTDLP_FIXTURE.read_text(encoding="utf-8"))
_NEWEST_URL = "https://www.youtube.com/watch?v=7c_ieWfAbrw"
_NEWEST_TITLE = "This AI News Week: New Models, Agents, and Robotics Breakthroughs"
_YTDLP_TITLE = "GPT 5.6, Mythos ban lifted, realtime avatars, Seedance 2.5, brain ultrasound: AI NEWS"


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url="rss", code=code, msg="err", hdrs=None, fp=None)


class _Fetch:
    """A fetch seam that fails ``fail_times`` with ``code`` then serves the feed."""

    def __init__(self, fail_times: int, code: int, body: bytes = _FEED) -> None:
        self.fail_times = fail_times
        self.code = code
        self.body = body
        self.calls = 0

    def __call__(self, url: str) -> bytes:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise _http_error(self.code)
        return self.body


class _Sleep:
    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


class ParseLatest(unittest.TestCase):
    def test_picks_newest_entry(self) -> None:
        url, title = _parse_latest(_FEED)
        self.assertEqual(url, _NEWEST_URL)
        self.assertEqual(title, _NEWEST_TITLE)

    def test_empty_feed_raises(self) -> None:
        empty = b'<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>'
        with self.assertRaises(RuntimeError):
            _parse_latest(empty)


class GetLatestVideoUrl(unittest.TestCase):
    def test_first_try_succeeds(self) -> None:
        fetch, sleep = _Fetch(fail_times=0, code=404), _Sleep()
        url, title = get_latest_video_url(fetch=fetch, sleep=sleep)
        self.assertEqual((url, title), (_NEWEST_URL, _NEWEST_TITLE))
        self.assertEqual(fetch.calls, 1)
        self.assertEqual(sleep.calls, [])  # no backoff needed

    def test_retries_transient_404_then_succeeds(self) -> None:
        fetch, sleep = _Fetch(fail_times=2, code=404), _Sleep()
        url, _ = get_latest_video_url(fetch=fetch, attempts=3, backoff=2.0, sleep=sleep)
        self.assertEqual(url, _NEWEST_URL)
        self.assertEqual(fetch.calls, 3)  # two failures + one success
        self.assertEqual(sleep.calls, [2.0, 4.0])  # linear backoff between tries

    def test_gives_up_after_attempts_on_sustained_500(self) -> None:
        fetch, sleep = _Fetch(fail_times=99, code=500), _Sleep()
        with self.assertRaises(RuntimeError):
            get_latest_video_url(
                fetch=fetch, attempts=3, backoff=1.0, sleep=sleep, fallback=None
            )
        self.assertEqual(fetch.calls, 3)  # bounded — no infinite loop
        self.assertEqual(len(sleep.calls), 2)  # slept between the 3 attempts only


class YtdlpFallback(unittest.TestCase):
    def test_parse_flat_picks_newest_entry(self) -> None:
        url, title = _parse_ytdlp_flat(_YTDLP_FLAT)
        self.assertEqual(url, _NEWEST_URL)
        self.assertEqual(title, _YTDLP_TITLE)

    def test_parse_flat_empty_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            _parse_ytdlp_flat({"entries": []})

    def test_parse_flat_builds_url_from_id_when_url_missing(self) -> None:
        url, title = _parse_ytdlp_flat({"entries": [{"id": "abc123", "title": "T"}]})
        self.assertEqual(url, "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(title, "T")

    def test_rss_throttled_recovers_via_fallback(self) -> None:
        fetch, sleep = _Fetch(fail_times=99, code=404), _Sleep()
        fallback = lambda: _parse_ytdlp_flat(_YTDLP_FLAT)  # noqa: E731
        url, title = get_latest_video_url(
            fetch=fetch, attempts=3, backoff=1.0, sleep=sleep, fallback=fallback
        )
        self.assertEqual(url, _NEWEST_URL)
        self.assertEqual(title, _YTDLP_TITLE)
        self.assertEqual(fetch.calls, 3)  # RSS fully exhausted first

    def test_fallback_failure_raises_after_rss_exhausted(self) -> None:
        fetch, sleep = _Fetch(fail_times=99, code=500), _Sleep()

        def broken_fallback() -> tuple[str, str]:
            raise RuntimeError("yt-dlp down too")

        with self.assertRaises(RuntimeError):
            get_latest_video_url(
                fetch=fetch, attempts=2, backoff=1.0, sleep=sleep, fallback=broken_fallback
            )


class AttachVideoMetadata(unittest.TestCase):
    def test_stores_description_on_category(self) -> None:
        cat = attach_video_metadata(
            {"id": "aisearch", "stories": []},
            {
                "url": "https://www.youtube.com/watch?v=abc",
                "title": "Episode",
                "upload_date": "20260702",
                "description": "paper: https://github.com/deepseek-ai/DeepSpark",
            },
        )
        self.assertEqual(cat["_video_description"], "paper: https://github.com/deepseek-ai/DeepSpark")
        self.assertEqual(cat["_video_url"], "https://www.youtube.com/watch?v=abc")


class AisearchDescriptionIngestion(unittest.TestCase):
    def test_build_ingestion_context_includes_description(self) -> None:
        from pipeline.editorial import build_ingestion_context, extract_aisearch_description

        desc = (_DATA / "theaisearch_description_sample.txt").read_text(encoding="utf-8").strip()
        skeleton = {
            "categories": [
                {
                    "id": "aisearch",
                    "stories": [],
                    "_video_description": desc,
                }
            ]
        }
        self.assertEqual(extract_aisearch_description(skeleton["categories"]), desc)
        ctx = build_ingestion_context(skeleton, [])
        self.assertIn("theAIsearch video description", ctx)
        self.assertIn("github.com/deepseek-ai/deepspark", ctx.lower())

    def test_description_urls_count_as_grounded(self) -> None:
        from pipeline.grounding import collect_skeleton_urls, is_ungrounded

        desc = (_DATA / "theaisearch_description_sample.txt").read_text(encoding="utf-8").strip()
        skeleton = {"categories": [{"id": "aisearch", "stories": [], "_video_description": desc}]}
        allow = collect_skeleton_urls(skeleton)
        self.assertIn("github.com/deepseek-ai/deepspark", allow)
        self.assertFalse(
            is_ungrounded(
                "https://github.com/deepseek-ai/DeepSpark",
                roots=set(),
                allow_urls=allow,
            )
        )


if __name__ == "__main__":
    unittest.main()
