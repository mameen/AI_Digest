"""
Fetch typography and font news from primary sources.

Sources:
  - Monotype Newsroom      https://www.monotype.com/newsroom
  - Monotype Resources     https://www.monotype.com/resources
  - I Love Typography      https://ilovetypography.com
  - Adobe Fonts Blog       https://blog.adobe.com/en/topics/fonts
  - MyFonts Blog           https://www.myfonts.com/pages/blog
  - Typographica           https://typographica.org

Outputs
-------
--json      Raw scraped articles (title + URL per source)
--stories   Story-card JSON ready to merge into the daily digest
            Shape: {"category": "typography", "icon": "🔤", "stories": [...]}

Usage:
    python skills/ai-news-digest/scripts/fetch_typography_news.py --stories
    python skills/ai-news-digest/scripts/fetch_typography_news.py --json
    python skills/ai-news-digest/scripts/fetch_typography_news.py --ai-only --stories
"""

import argparse
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

# Shared story-card helpers (sibling module)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from _story_utils import make_story, make_category

# ── AI / font relevance keywords ──────────────────────────────────────────────
AI_KEYWORDS = {
    "ai", "artificial intelligence", "machine learning", "ml", "neural",
    "generative", "gpt", "llm", "search", "discovery", "recommendation",
    "font search", "type search", "ai font", "font ai", "text rendering",
    "variable font", "opentype", "monotype fonts", "myfonts", "adobe fonts",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


# ── Generic HTML helpers ───────────────────────────────────────────────────────

from html.parser import HTMLParser


class _LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[dict] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href and not href.startswith(("#", "javascript", "mailto")):
                self._href = href
                self._text = []

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            text = re.sub(r"\s+", " ", " ".join(self._text)).strip()
            if text and len(text) > 5:
                self.links.append({"href": self._href, "text": text})
            self._href = None

    def handle_data(self, data):
        if self._href:
            self._text.append(data.strip())


def _fetch_html(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def _extract_links(html: str) -> list[dict]:
    p = _LinkExtractor()
    p.feed(html)
    return p.links


def _absolute(href: str, base: str) -> str:
    if href.startswith("http"):
        return href
    if href.startswith("//"):
        return "https:" + href
    return base.rstrip("/") + ("" if href.startswith("/") else "/") + href.lstrip("/")


_NAV_TITLE_TOKENS = {
    "sign up", "subscribe", "newsletter", "log in", "login", "register",
    "contact us", "about us", "privacy policy", "terms of", "cookie",
    "follow us", "read more", "learn more", "view all", "see all",
    "shop now", "buy now", "get started", "back to",
}

def _is_article_url(href: str) -> bool:
    bad = ["/search", "/tag", "/category", "/page/", "/wp-content",
           ".css", ".js", ".png", ".jpg", ".svg", "?s=", "#", "/feed", "/rss"]
    return not any(p in href for p in bad)

def _is_nav_title(title: str) -> bool:
    """Return True if the title looks like a navigation/CTA link, not an article."""
    t = title.lower()
    return any(tok in t for tok in _NAV_TITLE_TOKENS)


def _is_ai_related(text: str) -> bool:
    return any(kw in text.lower() for kw in AI_KEYWORDS)


def _scrape(url: str, domain: str, path_filter: str, source: str,
            limit: int, ai_only: bool) -> list[dict]:
    """Generic scraper: fetch URL, collect on-domain article links."""
    try:
        html = _fetch_html(url)
    except Exception as e:
        return [{"error": str(e), "source": source, "url": url}]

    links = _extract_links(html)
    results, seen = [], set()
    for lnk in links:
        href = _absolute(lnk["href"], f"https://{domain}")
        title = lnk["text"]
        if domain not in href:
            continue
        if path_filter and path_filter not in href:
            continue
        if not _is_article_url(href):
            continue
        if len(title) < 20 or title in seen:
            continue
        if _is_nav_title(title):
            continue
        if ai_only and not _is_ai_related(title):
            continue
        seen.add(title)
        results.append({"source": source, "title": title, "url": href})
        if len(results) >= limit:
            break
    return results


# ── Per-source fetchers ────────────────────────────────────────────────────────

def fetch_monotype_newsroom(ai_only=False)  -> list[dict]:
    return _scrape("https://www.monotype.com/newsroom",
                   "monotype.com", "", "Monotype Newsroom", 15, ai_only)

def fetch_monotype_resources(ai_only=False) -> list[dict]:
    return _scrape("https://www.monotype.com/resources",
                   "monotype.com", "/resources/", "Monotype Resources", 15, ai_only)

def fetch_ilovetypography(ai_only=False)    -> list[dict]:
    return _scrape("https://ilovetypography.com",
                   "ilovetypography.com", "", "I Love Typography", 10, ai_only)

def fetch_adobe_fonts_blog(ai_only=False)   -> list[dict]:
    return _scrape("https://blog.adobe.com/en/topics/fonts",
                   "blog.adobe.com", "", "Adobe Fonts Blog", 10, ai_only)

def fetch_typographica(ai_only=False)       -> list[dict]:
    return _scrape("https://typographica.org",
                   "typographica.org", "", "Typographica", 10, ai_only)

def fetch_myfonts_blog(ai_only=False)       -> list[dict]:
    return _scrape("https://www.myfonts.com/pages/blog",
                   "myfonts.com", "/blog", "MyFonts Blog", 10, ai_only)


FETCHERS = [
    ("monotype_newsroom",  fetch_monotype_newsroom),
    ("monotype_resources", fetch_monotype_resources),
    ("ilovetypography",    fetch_ilovetypography),
    ("adobe_fonts_blog",   fetch_adobe_fonts_blog),
    ("typographica",       fetch_typographica),
    ("myfonts_blog",       fetch_myfonts_blog),
]


# ── Orchestrator ───────────────────────────────────────────────────────────────

def fetch_all(ai_only: bool = False) -> dict[str, list[dict]]:
    """Run all fetchers in parallel. Returns {source_key: [article, ...]}."""
    results = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fn, ai_only): name for name, fn in FETCHERS}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = [{"error": str(e), "source": name}]
    return results


def to_story_cards(raw_results: dict[str, list[dict]]) -> list[dict]:
    """Convert raw scraped articles to digest story-card dicts (deduped by URL)."""
    stories, seen_urls = [], set()
    for articles in raw_results.values():
        for a in articles:
            if "error" in a or a["url"] in seen_urls:
                continue
            seen_urls.add(a["url"])
            stories.append(make_story(
                a["title"], a["url"], a["source"],
                extra_tags=["typography", "fonts"],
            ))
    return stories


def fetch_stories(ai_only: bool = False) -> dict:
    """Return a category envelope ready to embed in the partial digest JSON."""
    raw = fetch_all(ai_only=ai_only)
    return make_category("typography", to_story_cards(raw))


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch typography & font news")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stories", action="store_true",
                      help="Output story-card JSON (for digest merging)")
    mode.add_argument("--json", action="store_true", dest="raw_json",
                      help="Output raw scraped data")
    parser.add_argument("--ai-only", action="store_true",
                        help="Only return AI-related articles")
    args = parser.parse_args()

    print("Fetching typography sources…", file=sys.stderr)
    raw = fetch_all(ai_only=args.ai_only)

    if args.stories:
        print(json.dumps(make_category("typography", to_story_cards(raw)),
                         indent=2, ensure_ascii=False))
        return

    if args.raw_json:
        print(json.dumps(raw, indent=2, ensure_ascii=False))
        return

    # Human-readable default
    total = 0
    for key, articles in raw.items():
        real = [a for a in articles if "error" not in a]
        errors = [a for a in articles if "error" in a]
        print(f"\n── {key} ({len(real)} articles) ──")
        for a in real:
            print(f"  • {a['title'][:80]}")
            print(f"    {a['url']}")
        for e in errors:
            print(f"  ⚠ {e['error']}", file=sys.stderr)
        total += len(real)
    print(f"\nTotal: {total} articles across {len(raw)} sources")


if __name__ == "__main__":
    main()
