"""Playlist extraction utility tests — fixture-driven and deterministic."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from lib.youtube_playlist import extract_entries_from_payload, extract_playlist_entries

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "youtube_playlist_sample.json"


class _FakeCompleted:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout


class YoutubePlaylistUtilTest(unittest.TestCase):
    def test_extract_entries_from_payload(self) -> None:
        payload = json.loads(_FIXTURE.read_text(encoding="utf-8"))
        entries = extract_entries_from_payload(payload)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].index, 1)
        self.assertEqual(entries[0].title, "Video One")
        self.assertEqual(entries[1].url, "https://www.youtube.com/watch?v=bbbb")

    def test_extract_playlist_entries_with_runner(self) -> None:
        fixture_text = _FIXTURE.read_text(encoding="utf-8")

        def _runner(cmd, capture_output, text, check):
            self.assertIn("yt-dlp", cmd[0])
            self.assertEqual(cmd[1:4], ["--no-update", "--flat-playlist", "--dump-single-json"])
            self.assertTrue(capture_output)
            self.assertTrue(text)
            self.assertTrue(check)
            return _FakeCompleted(stdout=fixture_text)

        entries = extract_playlist_entries("https://youtube.com/playlist?list=PL_SAMPLE", runner=_runner)
        self.assertEqual([e.title for e in entries], ["Video One", "Video Two"])


if __name__ == "__main__":
    unittest.main()
