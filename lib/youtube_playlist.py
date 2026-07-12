"""Reusable helpers for extracting YouTube playlist entries via yt-dlp."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class PlaylistEntry:
    index: int
    title: str
    url: str


def extract_entries_from_payload(payload: dict[str, Any]) -> list[PlaylistEntry]:
    """Convert a yt-dlp playlist payload into ordered playlist entries."""
    entries: list[PlaylistEntry] = []
    raw_entries = payload.get("entries") or []
    for idx, item in enumerate(raw_entries, 1):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        title = str(item.get("title") or "").strip()
        if not url:
            continue
        entries.append(PlaylistEntry(index=idx, title=title, url=url))
    return entries


def extract_playlist_entries(
    playlist_url: str,
    *,
    runner: Callable[..., Any] = subprocess.run,
) -> list[PlaylistEntry]:
    """Fetch playlist entries with yt-dlp and return ordered title/url rows."""
    completed = runner(
        [
            "yt-dlp",
            "--no-update",
            "--flat-playlist",
            "--dump-single-json",
            playlist_url,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("Expected yt-dlp to return a JSON object payload")
    return extract_entries_from_payload(payload)
