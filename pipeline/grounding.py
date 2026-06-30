"""Source-grounding guard: keep the topic, but never ship a fabricated link.

Gap-filled categories (image-gen, design-ai, robotics, …) have no scraped
article feed, so the LLM can fabricate a ``source`` name and attach either a
leaderboard *root* URL it saw (e.g. ``arena.ai/leaderboard/text-to-image``) or
a plausible-looking deep path it never saw (e.g. ``figure.ai/blog/<slug>``,
which 404s). Both mislead the reader.

This module is the pipeline's deterministic self-check (a "reflection" pass that
needs no second LLM call, which offline can't tell a real link from a convincing
fake). A story is *ungrounded* when its ``url`` is a known crawl/structured
**root**, a bare domain, or — when an ingestion-context allow-set is supplied —
a URL the model was never actually shown. The ``leaderboard`` category
legitimately cites those roots, so it is exempt.

Policy: ``annotate_ungrounded`` *keeps the topic* and demotes only the link
(``url`` → ``None`` + ``source_pending``) so a real development is never lost
just because no verifiable URL exists. ``strip_ungrounded`` (drop) is retained
for callers that want the older behaviour.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

_SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s<>()\[\]\"'\\]+", re.IGNORECASE)
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


def collect_ingestion_urls(ingestion: str) -> set[str]:
    """Normalized set of every ``http(s)`` URL present in the ingestion context.

    This is the allow-set the model was actually shown. A gap story citing a URL
    outside it (a path the model invented) is provably ungrounded — the deep-path
    404 case the root-only check cannot catch.
    """
    urls: set[str] = set()
    for raw in _URL_RE.findall(ingestion or ""):
        urls.add(normalize_url(raw.rstrip(".,;")))
    urls.discard("")
    return urls


def is_ungrounded(url: str, roots: set[str], *, allow_urls: set[str] | None = None) -> bool:
    """True when ``url`` is unusable as an article link.

    Ungrounded when the URL is empty, a bare domain, a known leaderboard root,
    or — when ``allow_urls`` is supplied — absent from the ingestion context the
    model was shown (i.e. an invented path).
    """
    n = normalize_url(url)
    if not n:
        return True
    if n in roots:
        return True
    if "/" not in n:  # bare domain, no article path
        return True
    if allow_urls is not None and n not in allow_urls:
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


def annotate_ungrounded(
    categories: list[dict[str, Any]],
    roots: set[str],
    *,
    ingestion_urls: set[str] | None = None,
    exempt_ids: frozenset[str] = _EXEMPT_CATEGORY_IDS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep every story; demote the link instead of dropping the topic.

    For non-exempt categories, a story whose ``url`` is ungrounded (bare root /
    domain, or absent from ``ingestion_urls`` when supplied) keeps its title and
    summary but has ``url`` cleared to ``None`` and ``source_pending`` set, so a
    real development is never lost for lack of a verifiable link. Returns
    ``(categories, demoted)``.
    """
    out: list[dict[str, Any]] = []
    demoted: list[dict[str, Any]] = []
    for cat in categories:
        cid = cat.get("id")
        cat_copy = dict(cat)
        if cid in exempt_ids:
            out.append(cat_copy)
            continue
        new_stories: list[dict[str, Any]] = []
        for story in cat.get("stories") or []:
            if is_ungrounded(str(story.get("url") or ""), roots, allow_urls=ingestion_urls):
                demoted.append(
                    {
                        "category": cid,
                        "title": story.get("title"),
                        "source": story.get("source"),
                        "url": story.get("url"),
                    }
                )
                s = dict(story)
                s["url"] = None
                s["source_pending"] = True
                new_stories.append(s)
            else:
                new_stories.append(story)
        cat_copy["stories"] = new_stories
        out.append(cat_copy)
    return out, demoted


def find_ungrounded(
    categories: list[dict[str, Any]],
    roots: set[str],
    *,
    exempt_ids: frozenset[str] = _EXEMPT_CATEGORY_IDS,
) -> list[dict[str, Any]]:
    """Non-destructive view of offenders (used by validation)."""
    _, dropped = strip_ungrounded(categories, roots, exempt_ids=exempt_ids, drop_empty=False)
    return dropped
