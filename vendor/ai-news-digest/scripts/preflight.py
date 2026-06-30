"""
Pre-fetch all digest sources and write a partial digest JSON.

The output file is a near-complete digest skeleton: categories with story cards
already populated for aisearch, typography, and research. Claude reads this file
at Step 2 and only needs to:

  1. web_fetch the 7 JS-rendered leaderboard pages (listed in requires_web_fetch)
  2. Write a 2–3 sentence summary for each story  (significance/novelty/relevance_design = 0 means "unscored")
  3. Assign significance / novelty / relevance_design scores (1–5)
  4. Add the leaderboard, llm, image-gen, design-ai, and robotics categories
  5. Compute visualizations block and top_stories
  6. Save as the final YYYYMMDDHHMMSS.json + .html

What this script fetches (all in parallel, ~15s):
  ✓ theAIsearch  — latest video via RSS + yt-dlp (every chapter → story card)
  ✓ Typography   — Monotype, I Love Typography, Adobe Fonts Blog, Typographica, MyFonts
  ✓ Research     — HuggingFace Papers (top 20) + arXiv cs.AI / cs.CV / cs.CL
  ✓ LLM Stats    — llm-stats.com/llm-updates raw text (for Claude to parse)

Not fetched (JS-rendered SPAs — Claude's web_fetch handles these):
  ✗ Artificial Analysis Intelligence Leaderboard
  ✗ Vellum LLM + Open Leaderboards
  ✗ AA Image Arena
  ✗ Arena.ai Text-to-Image Leaderboard
  ✗ Arena.ai Text-to-Video Leaderboard
  ✗ AA Text-to-Video Leaderboard

Output:  .preflight/preflight_YYYYMMDDHHMMSS.json

Usage:
    python skills/ai-news-digest/scripts/preflight.py
    python skills/ai-news-digest/scripts/preflight.py --prefix 20260509120000
    python skills/ai-news-digest/scripts/preflight.py --json   # stdout only
"""

import argparse
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

# ── Sibling modules ────────────────────────────────────────────────────────────
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from fetch_typography_news  import fetch_stories as fetch_typography_stories
from fetch_research_papers  import fetch_stories as fetch_research_stories
from fetch_video_chapters   import (
    get_latest_video_url, fetch_video_info, to_story_cards as chapters_to_stories,
    make_category,
)
from _story_utils   import CATEGORY_META
from _cache_utils   import cache_write, cache_read, cache_stale, build_prefix as _build_prefix

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_DIR = SCRIPTS_DIR.parent.parent.parent
PREFLIGHT_DIR = PROJECT_DIR / ".preflight"

# ── JS-rendered leaderboards — always need Claude's web_fetch ─────────────────
REQUIRES_WEB_FETCH = [
    {
        "label":    "AA Intelligence Leaderboard",
        "url":      "https://artificialanalysis.ai/leaderboards/models",
        "category": "leaderboard",
        "priority": "HIGH",
        "why":      "Top 5 by intelligence score, rank changes, closed vs open comparison",
    },
    {
        "label":    "Vellum LLM Leaderboard",
        "url":      "https://www.vellum.ai/llm-leaderboard",
        "category": "leaderboard",
        "priority": "HIGH",
        "why":      "GPQA, AIME, SWE-bench, FrontierMath scores",
    },
    {
        "label":    "Vellum Open LLM Leaderboard",
        "url":      "https://www.vellum.ai/open-llm-leaderboard",
        "category": "leaderboard",
        "priority": "HIGH",
        "why":      "Best open-weight model, open vs closed gap",
    },
    {
        "label":    "AA Image Arena (Text-to-Image)",
        "url":      "https://artificialanalysis.ai/image/leaderboard/text-to-image",
        "category": "image-gen",
        "priority": "HIGH",
        "why":      "Top image gen Elo scores",
    },
    {
        "label":    "Arena.ai Text-to-Image Leaderboard",
        "url":      "https://arena.ai/leaderboard/text-to-image",
        "category": "image-gen",
        "priority": "HIGH",
        "why":      "Text Rendering subcategory specifically — cross-post to typography",
    },
    {
        "label":    "Arena.ai Text-to-Video Leaderboard",
        "url":      "https://arena.ai/leaderboard/text-to-video",
        "category": "image-gen",
        "priority": "HIGH",
        "why":      "Top text-to-video Elo scores (Sora, Veo, Kling, Seedance)",
    },
    {
        "label":    "AA Text-to-Video Leaderboard",
        "url":      "https://artificialanalysis.ai/video/leaderboard/text-to-video",
        "category": "image-gen",
        "priority": "HIGH",
        "why":      "Artificial Analysis video-gen Elo index",
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ── LLM Stats ─────────────────────────────────────────────────────────────────

def _fetch_llm_stats() -> dict:
    import re
    url = "https://llm-stats.com/llm-updates"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()
        return {"url": url, "raw_text": text[:8000]}
    except Exception as e:
        return {"url": url, "error": str(e)}


# ── theAIsearch ───────────────────────────────────────────────────────────────

def _fetch_aisearch_category() -> dict:
    url, rss_title = get_latest_video_url()
    print(f"  theAIsearch: {rss_title}", file=sys.stderr)
    info = fetch_video_info(url)
    stories = chapters_to_stories(info)
    print(f"  theAIsearch: {len(stories)} story cards", file=sys.stderr)
    cat = make_category("aisearch", stories)
    # Attach video metadata for the skill to use
    cat["_video_url"]   = info["url"]
    cat["_video_title"] = info["title"]
    cat["_upload_date"] = info.get("upload_date", "")
    return cat


# ── Orchestrator ───────────────────────────────────────────────────────────────

def build_prefix() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d120000")


def run_preflight(prefix: str, force: bool = False) -> dict:
    print(f"\n🚀  Preflight  prefix={prefix}", file=sys.stderr)
    print("─" * 52, file=sys.stderr)

    # Script name → cache key mapping
    CACHE_KEYS = {
        "aisearch":   "fetch_youtube",
        "typography": "fetch_typography",
        "research":   "fetch_research",
        "llm_stats":  "fetch_llm_stats",
    }

    section_fns = {
        "aisearch":   _fetch_aisearch_category,
        "typography": fetch_typography_stories,
        "research":   fetch_research_stories,
        "llm_stats":  _fetch_llm_stats,
    }

    # Check which sections can be served from cache
    sections: dict[str, dict] = {}
    needs_fetch: dict[str, callable] = {}

    for key, fn in section_fns.items():
        cache_key = CACHE_KEYS[key]
        if not force:
            cached = cache_read(prefix, cache_key)
            if cached is not None:
                sections[key] = cached
                n = len(cached.get("stories", [])) if key != "llm_stats" else "cached"
                print(f"  {key}: {n} stories (from cache)", file=sys.stderr)
                continue
        needs_fetch[key] = fn

    if needs_fetch:
        print(f"  Fetching {list(needs_fetch.keys())} in parallel…", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(fn): key for key, fn in needs_fetch.items()}
            for future in as_completed(futures):
                key = futures[future]
                cache_key = CACHE_KEYS[key]
                try:
                    result = future.result()
                    sections[key] = result
                    # Write to individual cache file
                    cache_write(result, prefix, cache_key)
                    if key != "llm_stats":
                        n = len(result.get("stories", []))
                        print(f"  {key}: {n} stories", file=sys.stderr)
                    else:
                        ok = "error" not in result
                        print(f"  llm_stats: {'✓' if ok else '✗ (see error key)'}", file=sys.stderr)
                except Exception as e:
                    print(f"\n  ❌ {key} FAILED: {e}", file=sys.stderr)
                    print(f"     This section will be missing from the preflight cache.", file=sys.stderr)
                    print(f"     Fix the error and re-run, or Claude will skip this category.", file=sys.stderr)
                    sections[key] = {"error": str(e), "script": cache_key}

    # Build canonical categories list (same order as the final digest)
    categories = []
    for cat_id in ("aisearch", "typography", "research"):
        sec = sections.get(cat_id, {})
        if "stories" in sec:
            categories.append(sec)

    payload = {
        "generated_at":       datetime.now(timezone.utc).isoformat(),
        "prefix":             prefix,
        "partial":            True,
        "note": (
            "Generated by preflight.py. Claude must: "
            "(1) web_fetch the URLs in requires_web_fetch to get leaderboard data, "
            "(2) write a 2–3 sentence summary for each story (summary is empty ''), "
            "(3) assign significance/novelty/relevance_design scores 1–5 (currently 0), "
            "(4) add leaderboard / llm / image-gen / design-ai / robotics categories, "
            "(5) compute visualizations block."
        ),
        "categories":         categories,
        "llm_stats":          sections.get("llm_stats", {}),
        "requires_web_fetch": REQUIRES_WEB_FETCH,
    }
    return payload


def save(data: dict, path: Path | None = None) -> Path:
    out = path or PREFLIGHT_DIR / f"preflight_{data['prefix']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pre-fetch all digest sources into a partial digest JSON"
    )
    parser.add_argument("--prefix", help="14-digit prefix (default: today noon UTC)")
    parser.add_argument("--output", help="Custom output path")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch all sections even if cache files exist")
    parser.add_argument("--json", action="store_true", dest="stdout_only",
                        help="Print to stdout instead of saving")
    args = parser.parse_args()

    prefix = args.prefix or build_prefix()
    data   = run_preflight(prefix, force=args.force)

    if args.stdout_only:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    saved = save(data, Path(args.output) if args.output else None)

    # Summary
    print("\n" + "─" * 52, file=sys.stderr)
    total_stories = sum(len(c.get("stories", [])) for c in data["categories"])
    cat_summary = ", ".join(
        f"{c['id']}:{len(c.get('stories',[]))}"
        for c in data["categories"]
    )
    print(f"✅  {total_stories} story cards  [{cat_summary}]", file=sys.stderr)
    print(f"   Still needs web_fetch ({len(REQUIRES_WEB_FETCH)}):", file=sys.stderr)
    for s in REQUIRES_WEB_FETCH:
        print(f"     • {s['label']}", file=sys.stderr)
    print(f"\n   Saved → {saved}", file=sys.stderr)
    print(f"\n   Tell Claude:\n"
          f"   \"Today's digest prefix is {prefix}. "
          f"Read .preflight/preflight_{prefix}.json, "
          f"enrich the stories, fetch the leaderboards, and produce the final digest.\"\n",
          file=sys.stderr)


if __name__ == "__main__":
    main()
