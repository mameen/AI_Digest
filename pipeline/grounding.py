"""Source-grounding guard: drop stories that cite no real article.

Gap-filled categories (image-gen, design-ai, …) have no scraped article feed,
so the LLM can fabricate a ``source`` name and attach whichever leaderboard
*root* URL it saw in the ingestion context (e.g. ``arena.ai/leaderboard/
text-to-image``). Those links open a leaderboard index, not the article the
card describes. This module flags such stories deterministically: a story is
*ungrounded* when its ``url`` is a known crawl/structured **root** or a bare
domain. The ``leaderboard`` category legitimately cites those roots, so it is
exempt.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_EXEMPT_CATEGORY_IDS = frozenset({"leaderboard"})


def normalize_url(url: str) -> str:
    """Lowercase host+path key: drop scheme, leading ``www.``, query/fragment, trailing ``/``."""
    s = (url or "").strip().lower()
    s = _SCHEME.sub("", s)
    if s.startswith("www."):
        s = s[4:]
    s = s.split("#", 1)[0].split("?", 1)[0]
    return s.rstrip("/")


def collect_roots(
    web_fetch_items: Iterable[Any] | None = None, *, include_structured: bool = True
) -> set[str]:
    """Normalized root URLs that are leaderboard indexes, not articles.

    Derived from the preflight ``requires_web_fetch`` list (each item is a dict
    with a ``url`` or a bare string) plus the structured-API source endpoints —
    no hand-maintained duplicate list.
    """
    roots: set[str] = set()
    for item in web_fetch_items or []:
        url = item.get("url") if isinstance(item, dict) else item
        if url:
            roots.add(normalize_url(str(url)))
    if include_structured:
        try:
            from pipeline.structured_sources import STRUCTURED_SOURCES

            for src in STRUCTURED_SOURCES:
                if src.get("url"):
                    roots.add(normalize_url(src["url"]))
        except Exception:
            pass
    roots.discard("")
    return roots


def is_ungrounded(url: str, roots: set[str]) -> bool:
    """True when ``url`` is a bare domain or one of the known leaderboard roots."""
    n = normalize_url(url)
    if not n:
        return True
    if n in roots:
        return True
    if "/" not in n:  # bare domain, no article path
        return True
    return False


def strip_ungrounded(
    categories: list[dict[str, Any]],
    roots: set[str],
    *,
    exempt_ids: frozenset[str] = _EXEMPT_CATEGORY_IDS,
    drop_empty: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(kept_categories, dropped_stories)``.

    Stories whose ``url`` is ungrounded are removed from non-exempt categories.
    Categories left empty are dropped when ``drop_empty`` (an empty card reads
    as broken in the widget).
    """
    kept: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for cat in categories:
        cid = cat.get("id")
        if cid in exempt_ids:
            kept.append(cat)
            continue
        stories = cat.get("stories") or []
        survivors: list[dict[str, Any]] = []
        for story in stories:
            if is_ungrounded(str(story.get("url") or ""), roots):
                dropped.append(
                    {
                        "category": cid,
                        "title": story.get("title"),
                        "source": story.get("source"),
                        "url": story.get("url"),
                    }
                )
            else:
                survivors.append(story)
        if survivors or not drop_empty:
            cat_copy = dict(cat)
            cat_copy["stories"] = survivors
            kept.append(cat_copy)
    return kept, dropped


def find_ungrounded(
    categories: list[dict[str, Any]],
    roots: set[str],
    *,
    exempt_ids: frozenset[str] = _EXEMPT_CATEGORY_IDS,
) -> list[dict[str, Any]]:
    """Non-destructive view of offenders (used by validation)."""
    _, dropped = strip_ungrounded(categories, roots, exempt_ids=exempt_ids, drop_empty=False)
    return dropped
