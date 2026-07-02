"""
Fetch robotics & embodied-AI news from primary RSS/Atom feeds.

Sources (all verified live, per-article URLs, on-topic):
  - The Robot Report        https://www.therobotreport.com/feed/
  - IEEE Spectrum Robotics  https://spectrum.ieee.org/feeds/topic/robotics.rss
  - Robohub                 https://robohub.org/feed/

These are real syndication feeds (not JS-rendered SPAs), so a lightweight
``urllib`` + ``ElementTree`` parse yields grounded story cards directly — the
same robust pattern the typography/research fetchers use. This makes robotics a
curated skeleton category rather than an LLM gap-fill, so it is grounded every
run instead of depending on the model recycling prior links.

Outputs
-------
--json      Raw parsed articles (title + URL per source)
--stories   Story-card JSON ready to merge into the daily digest
            Shape: {"id": "robotics", "icon": "🤖", "stories": [...]}

Usage:
    python skills/ai-news-digest/scripts/fetch_robotics_news.py --stories
    python skills/ai-news-digest/scripts/fetch_robotics_news.py --json
"""

import argparse
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

# Shared story-card helpers (sibling module)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from _story_utils import make_story, make_category

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml",
}

_ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}

# label → (feed url, per-source limit)
SOURCES: dict[str, tuple[str, int]] = {
    "The Robot Report":       ("https://www.therobotreport.com/feed/", 10),
    "IEEE Spectrum Robotics": ("https://spectrum.ieee.org/feeds/topic/robotics.rss", 10),
    "Robohub":                ("https://robohub.org/feed/", 10),
}


# ── Feed I/O + parse ───────────────────────────────────────────────────────────

def _fetch(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def parse_feed(xml_bytes: bytes, source: str, limit: int = 10) -> list[dict]:
    """Parse an RSS or Atom feed into ``{source, title, url}`` article dicts."""
    root = ET.fromstring(xml_bytes)
    out: list[dict] = []
    seen: set[str] = set()

    items = root.findall(".//item")  # RSS
    if items:
        for it in items:
            title = (it.findtext("title") or "").strip()
            url = (it.findtext("link") or "").strip()
            if title and url and url not in seen:
                seen.add(url)
                out.append({"source": source, "title": title, "url": url})
            if len(out) >= limit:
                break
        return out

    for entry in root.findall(".//a:entry", _ATOM_NS):  # Atom
        title = (entry.findtext("a:title", default="", namespaces=_ATOM_NS) or "").strip()
        link_el = entry.find("a:link", _ATOM_NS)
        url = (link_el.get("href") if link_el is not None else "") or ""
        url = url.strip()
        if title and url and url not in seen:
            seen.add(url)
            out.append({"source": source, "title": title, "url": url})
        if len(out) >= limit:
            break
    return out


def fetch_source(source: str, url: str, limit: int, *, fetch=_fetch) -> list[dict]:
    try:
        return parse_feed(fetch(url), source, limit)
    except Exception as e:
        return [{"error": str(e), "source": source, "url": url}]


# ── Orchestrator ───────────────────────────────────────────────────────────────

def fetch_all(*, fetch=_fetch) -> dict[str, list[dict]]:
    """Fetch all robotics feeds in parallel. Returns {source: [article, ...]}."""
    results: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        futures = {
            pool.submit(fetch_source, src, url, lim, fetch=fetch): src
            for src, (url, lim) in SOURCES.items()
        }
        for future in as_completed(futures):
            src = futures[future]
            try:
                results[src] = future.result()
            except Exception as e:
                results[src] = [{"error": str(e), "source": src}]
    return results


def to_story_cards(raw_results: dict[str, list[dict]]) -> list[dict]:
    """Convert parsed articles to digest story-card dicts (deduped by URL)."""
    stories, seen_urls = [], set()
    for articles in raw_results.values():
        for a in articles:
            if "error" in a or a["url"] in seen_urls:
                continue
            seen_urls.add(a["url"])
            stories.append(make_story(
                a["title"], a["url"], a["source"],
                id_prefix="robo", extra_tags=["robotics", "embodied-ai"],
            ))
    return stories


def fetch_stories(*, fetch=_fetch) -> dict:
    """Return a category envelope ready to embed in the partial digest JSON."""
    return make_category("robotics", to_story_cards(fetch_all(fetch=fetch)))


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch robotics & embodied-AI news")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stories", action="store_true", help="Story-card JSON")
    mode.add_argument("--json", action="store_true", dest="raw_json", help="Raw parsed data")
    args = parser.parse_args()

    print("Fetching robotics sources…", file=sys.stderr)
    raw = fetch_all()

    if args.stories:
        print(json.dumps(make_category("robotics", to_story_cards(raw)),
                         indent=2, ensure_ascii=False))
        return
    if args.raw_json:
        print(json.dumps(raw, indent=2, ensure_ascii=False))
        return

    total = 0
    for src, articles in raw.items():
        real = [a for a in articles if "error" not in a]
        print(f"\n── {src} ({len(real)} articles) ──")
        for a in real:
            print(f"  • {a['title'][:80]}")
            print(f"    {a['url']}")
        for e in [a for a in articles if "error" in a]:
            print(f"  ⚠ {e['error']}", file=sys.stderr)
        total += len(real)
    print(f"\nTotal: {total} articles across {len(raw)} sources")


if __name__ == "__main__":
    main()
