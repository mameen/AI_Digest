"""RSS / Atom feed extractor — generic, not tied to robotics or any topic."""

from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse

from lib.ingest.types import ResearchBullet

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml",
}

_ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}
_CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"


@dataclass(frozen=True)
class FeedSpec:
    """One syndication feed — label is provenance (e.g. source name), not a topic id."""

    label: str
    url: str
    limit: int = 10


def _url_ok(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    return bool((parsed.path or "").strip("/"))


def _fetch(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _item_body_html(item: ET.Element) -> str:
    return (item.findtext(_CONTENT_NS) or item.findtext("description") or "").strip()


def _atom_body_html(entry: ET.Element) -> str:
    content = entry.findtext("a:content", default="", namespaces=_ATOM_NS) or ""
    summary = entry.findtext("a:summary", default="", namespaces=_ATOM_NS) or ""
    return (content or summary).strip()


def parse_feed(xml_bytes: bytes, source: str, limit: int = 10) -> list[dict]:
    """Parse RSS or Atom into ``{source, title, url, body_html}`` article dicts."""
    root = ET.fromstring(xml_bytes)
    out: list[dict] = []
    seen: set[str] = set()

    items = root.findall(".//item")
    if items:
        for it in items:
            title = (it.findtext("title") or "").strip()
            url = (it.findtext("link") or "").strip()
            if title and url and url not in seen and _url_ok(url):
                seen.add(url)
                out.append(
                    {
                        "source": source,
                        "title": title,
                        "url": url,
                        "body_html": _item_body_html(it),
                    }
                )
            if len(out) >= limit:
                break
        return out

    for entry in root.findall(".//a:entry", _ATOM_NS):
        title = (entry.findtext("a:title", default="", namespaces=_ATOM_NS) or "").strip()
        link_el = entry.find("a:link", _ATOM_NS)
        url = (link_el.get("href") if link_el is not None else "") or ""
        url = url.strip()
        if title and url and url not in seen and _url_ok(url):
            seen.add(url)
            out.append(
                {
                    "source": source,
                    "title": title,
                    "url": url,
                    "body_html": _atom_body_html(entry),
                }
            )
        if len(out) >= limit:
            break
    return out


def fetch_feed_bytes(url: str, *, timeout: int = 15) -> bytes:
    """Fetch feed XML from HTTP(S) or ``eval:<fixture-name>`` under tests/data/evaluation/."""
    if url.startswith("eval:"):
        from lib.ingest.fixtures import evaluation_fixture_path

        path = evaluation_fixture_path(url[5:])
        if not path.is_file():
            raise FileNotFoundError(f"evaluation feed fixture missing: {path}")
        return path.read_bytes()
    return _fetch(url, timeout=timeout)


def fetch_feeds(
    feeds: list[FeedSpec],
    *,
    fetch: Callable[[str], bytes] | None = None,
) -> list[dict]:
    """Fetch many feeds in parallel; flatten to article dicts (dedupe by URL)."""
    fetch_fn = fetch or (lambda url: fetch_feed_bytes(url))
    results: list[dict] = []
    seen: set[str] = set()

    def _one(spec: FeedSpec) -> list[dict]:
        try:
            return parse_feed(fetch_fn(spec.url), spec.label, spec.limit)
        except Exception as exc:
            return [{"error": str(exc), "source": spec.label, "url": spec.url}]

    with ThreadPoolExecutor(max_workers=max(1, len(feeds))) as pool:
        futures = [pool.submit(_one, spec) for spec in feeds]
        for future in as_completed(futures):
            for article in future.result():
                if "error" in article:
                    continue
                url = article.get("url", "")
                if url in seen:
                    continue
                seen.add(url)
                results.append(article)
    return results


def articles_to_bullets(articles: list[dict], *, title_fmt: str = "{title}") -> list[ResearchBullet]:
    """Map parsed articles to researcher bullets."""
    bullets: list[ResearchBullet] = []
    for article in articles:
        title = str(article.get("title") or "").strip()
        url = str(article.get("url") or "").strip()
        source = str(article.get("source") or "").strip()
        if not title or not _url_ok(url):
            continue
        label = title_fmt.format(title=title, source=source)
        bullets.append(ResearchBullet(title=label, url=url, verified=True))
    return bullets
