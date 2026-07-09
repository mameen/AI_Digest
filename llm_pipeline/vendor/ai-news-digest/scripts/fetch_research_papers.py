"""
Fetch trending AI research papers from HuggingFace Papers and arXiv.

Sources:
  - HuggingFace Papers    https://huggingface.co/papers     (upvote-ranked, daily)
  - arXiv cs.AI           https://arxiv.org/list/cs.AI/recent
  - arXiv cs.CV           https://arxiv.org/list/cs.CV/recent
  - arXiv cs.CL           https://arxiv.org/list/cs.CL/recent  (NLP / text rendering)

Outputs
-------
--json      Raw scraped papers (title + URL + rank per source)
--stories   Story-card JSON ready to merge into the daily digest
            Shape: {"category": "research", "icon": "📄", "stories": [...]}

Usage:
    python skills/ai-news-digest/scripts/fetch_research_papers.py --stories
    python skills/ai-news-digest/scripts/fetch_research_papers.py --source hf --stories
    python skills/ai-news-digest/scripts/fetch_research_papers.py --json
"""

import argparse
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from datetime import datetime, timezone

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from _story_utils import make_story, make_category

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


def _fetch_html(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


# ── HuggingFace Papers ─────────────────────────────────────────────────────────

class _HFPapersParser(HTMLParser):
    """Collect <a href="/papers/ARXIV_ID"> links with their inner text."""
    def __init__(self):
        super().__init__()
        self.papers: list[dict] = []
        self._href = ""
        self._text: list[str] = []
        self._active = False

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href", "")
            if re.match(r"^/papers/\d{4}\.\d+", href):
                self._href = "https://huggingface.co" + href
                self._text = []
                self._active = True

    def handle_endtag(self, tag):
        if tag == "a" and self._active:
            title = re.sub(r"\s+", " ", " ".join(self._text)).strip()
            if title and len(title) > 10:
                self.papers.append({"title": title, "url": self._href})
            self._active = False

    def handle_data(self, data):
        if self._active:
            self._text.append(data.strip())


def fetch_huggingface_papers(limit: int = 20) -> list[dict]:
    url = "https://huggingface.co/papers"
    try:
        html = _fetch_html(url)
    except Exception as e:
        return [{"error": str(e), "source": "HuggingFace Papers", "url": url}]

    parser = _HFPapersParser()
    parser.feed(html)
    seen, results = set(), []
    for i, p in enumerate(parser.papers):
        if p["url"] in seen or not p["title"]:
            continue
        seen.add(p["url"])
        results.append({"source": "HuggingFace Papers", "rank": i + 1, **p})
        if len(results) >= limit:
            break
    return results


# ── arXiv ──────────────────────────────────────────────────────────────────────

def fetch_arxiv(category: str = "cs.AI", limit: int = 15) -> list[dict]:
    """
    Fetch recent papers from an arXiv category listing page.
    Uses regex on raw HTML — arXiv uses single-quoted attributes that
    confuse standard HTML parsers.
    """
    url = f"https://arxiv.org/list/{category}/recent"
    labels = {"cs.AI": "arXiv cs.AI", "cs.CV": "arXiv cs.CV", "cs.CL": "arXiv cs.CL"}
    source = labels.get(category, f"arXiv {category}")

    try:
        html = _fetch_html(url)
    except Exception as e:
        return [{"error": str(e), "source": source, "url": url}]

    # Each entry is a <dt>…abs link…</dt><dd>…title…</dd> pair
    pairs = re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", html, re.DOTALL)
    results, seen = [], set()
    for dt, dd in pairs[: limit * 2]:
        abs_m = re.search(r"href\s*=\s*[\"']?(/abs/[\w.]+)[\"']?", dt)
        title_m = re.search(
            r"list-title[^>]*>.*?<span[^>]*>Title:</span>\s*([^<]+)", dd, re.DOTALL
        )
        if not abs_m or not title_m:
            continue
        abs_url = "https://arxiv.org" + abs_m.group(1)
        title = re.sub(r"\s+", " ", title_m.group(1)).strip()
        if not title or abs_url in seen:
            continue
        seen.add(abs_url)
        results.append({"source": source, "title": title, "url": abs_url})
        if len(results) >= limit:
            break
    return results


# ── Orchestrator ───────────────────────────────────────────────────────────────

SOURCES = {
    "hf":       ("HuggingFace Papers", fetch_huggingface_papers),
    "arxiv-ai": ("arXiv cs.AI",        lambda: fetch_arxiv("cs.AI")),
    "arxiv-cv": ("arXiv cs.CV",        lambda: fetch_arxiv("cs.CV")),
    "arxiv-cl": ("arXiv cs.CL",        lambda: fetch_arxiv("cs.CL")),
}


def fetch_all() -> dict[str, list[dict]]:
    """Fetch all sources in parallel. Returns {source_key: [paper, ...]}."""
    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn): key for key, (_, fn) in SOURCES.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as e:
                results[key] = [{"error": str(e), "source": key}]
    return results


def to_story_cards(raw_results: dict[str, list[dict]]) -> list[dict]:
    """Convert raw papers to digest story-card dicts (deduped by URL)."""
    stories, seen_urls = [], set()

    # HuggingFace first (ranked by upvotes — highest quality signal)
    priority_order = ["hf", "arxiv-ai", "arxiv-cv", "arxiv-cl"]
    ordered = {k: raw_results[k] for k in priority_order if k in raw_results}
    ordered.update({k: v for k, v in raw_results.items() if k not in ordered})

    for papers in ordered.values():
        for p in papers:
            if "error" in p or p["url"] in seen_urls:
                continue
            seen_urls.add(p["url"])
            rank_snippet = f"HuggingFace Papers rank #{p['rank']}" if "rank" in p else ""
            stories.append(make_story(
                p["title"], p["url"], p["source"],
                raw_snippet=rank_snippet,
                extra_tags=["research"],
            ))
    return stories


def fetch_stories() -> dict:
    """Return a category envelope ready to embed in the partial digest JSON."""
    raw = fetch_all()
    return make_category("research", to_story_cards(raw))


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch AI research papers")
    parser.add_argument("--source", choices=list(SOURCES.keys()) + ["all"],
                        default="all", help="Which source(s) to fetch")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stories", action="store_true",
                      help="Output story-card JSON (for digest merging)")
    mode.add_argument("--json", action="store_true", dest="raw_json",
                      help="Output raw scraped data")
    args = parser.parse_args()

    print("Fetching research paper sources…", file=sys.stderr)

    if args.source == "all":
        raw = fetch_all()
    else:
        _, fn = SOURCES[args.source]
        raw = {args.source: fn()}

    if args.stories:
        print(json.dumps(make_category("research", to_story_cards(raw)),
                         indent=2, ensure_ascii=False))
        return

    if args.raw_json:
        print(json.dumps(raw, indent=2, ensure_ascii=False))
        return

    # Human-readable default
    total = 0
    for key, papers in raw.items():
        real = [p for p in papers if "error" not in p]
        label = SOURCES.get(key, (key,))[0]
        print(f"\n── {label} ({len(real)} papers) ──")
        for p in real:
            rank = f"#{p['rank']}  " if "rank" in p else ""
            print(f"  {rank}{p['title'][:80]}")
            print(f"       {p['url']}")
        for e in [p for p in papers if "error" in p]:
            print(f"  ⚠ {e['error']}", file=sys.stderr)
        total += len(real)
    print(f"\nTotal: {total} papers across {len(raw)} sources")


if __name__ == "__main__":
    main()
