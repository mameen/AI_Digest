"""RSS/Atom feed parser — fixture-backed, no external dependencies beyond stdlib.

parse_rss_file(path, source_id, limit) — parse a local file
parse_rss_bytes(data, source_id, limit) — parse raw bytes (same logic, useful for live fetch)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from kaggle_ai_agents.models import NewsItem

_ATOM_NS = "http://www.w3.org/2005/Atom"
_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"


def _text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return (el.text or "").strip()


def _parse_tree(root: ET.Element, source_id: str, limit: int) -> list[NewsItem]:
    items: list[NewsItem] = []

    # ── RSS 2.0 ───────────────────────────────────────────────────────────────
    channel = root.find("channel")
    if channel is not None:
        for el in channel.findall("item"):
            title = _text(el.find("title"))
            url = _text(el.find("link"))
            if not url:
                # Some feeds put the link as text in <guid isPermaLink="true">
                guid = el.find("guid")
                if guid is not None and guid.get("isPermaLink", "false").lower() == "true":
                    url = _text(guid)
            summary = _text(el.find("description")) or _text(el.find(_CONTENT_NS))
            if title and url and url.startswith("http"):
                items.append(NewsItem(source_id=source_id, title=title, url=url, summary=summary[:500]))
            if len(items) >= limit:
                break
        return items

    # ── Atom ─────────────────────────────────────────────────────────────────
    for el in root.findall(f"{{{_ATOM_NS}}}entry"):
        title = _text(el.find(f"{{{_ATOM_NS}}}title"))
        url = ""
        for link in el.findall(f"{{{_ATOM_NS}}}link"):
            rel = link.get("rel", "alternate")
            href = link.get("href", "")
            if rel in ("alternate", "") and href.startswith("http"):
                url = href
                break
        summary = _text(el.find(f"{{{_ATOM_NS}}}summary")) or _text(el.find(f"{{{_ATOM_NS}}}content"))
        if title and url:
            items.append(NewsItem(source_id=source_id, title=title, url=url, summary=summary[:500]))
        if len(items) >= limit:
            break

    return items


def parse_rss_bytes(data: bytes, source_id: str, limit: int = 20) -> list[NewsItem]:
    """Parse raw RSS/Atom bytes. Use this for both fixture-backed tests and live fetches."""
    root = ET.fromstring(data)
    return _parse_tree(root, source_id, limit)


def parse_rss_file(path: str | Path, source_id: str, limit: int = 20) -> list[NewsItem]:
    """Parse a local RSS/Atom file. Used in tests with committed fixtures."""
    data = Path(path).read_bytes()
    return parse_rss_bytes(data, source_id=source_id, limit=limit)
