"""Merge fresh agent stories into baseline categories without dropping carried rows."""

from __future__ import annotations

import copy
from typing import Any


def merge_stories_by_url(
    baseline_stories: list[dict[str, Any]],
    fresh_stories: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Fresh stories first; keep baseline rows whose URL is not superseded."""
    fresh_urls = {
        str(s.get("url") or "").strip()
        for s in fresh_stories
        if str(s.get("url") or "").strip()
    }
    kept = [
        copy.deepcopy(s)
        for s in baseline_stories
        if str(s.get("url") or "").strip() and str(s.get("url") or "").strip() not in fresh_urls
    ]
    return [copy.deepcopy(s) for s in fresh_stories] + kept
