"""
Fetch the latest theAIsearch YouTube video and extract its chapter list.

Outputs
-------
(default)   Human-readable chapter list
--json      Raw video metadata + chapters as JSON
--stories   Story-card JSON ready to merge into the daily digest
            Shape: {"category": "aisearch", "icon": "🔍", "stories": [...]}

Each chapter becomes one story card. The skill rule is: NEVER FILTER — every
chapter must be included regardless of perceived relevance.

Usage:
    python skills/ai-news-digest/scripts/fetch_video_chapters.py
    python skills/ai-news-digest/scripts/fetch_video_chapters.py --stories
    python skills/ai-news-digest/scripts/fetch_video_chapters.py --url https://...
    python skills/ai-news-digest/scripts/fetch_video_chapters.py --json

Requires: pip install yt-dlp
"""

import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
import urllib.error
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from _story_utils import make_story, make_category

CHANNEL_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id=UCIgnGlGkVRhd4qNFcEwLL4A"
CHANNEL_VIDEOS = "https://www.youtube.com/channel/UCIgnGlGkVRhd4qNFcEwLL4A/videos"
HEADERS = {"User-Agent": "Mozilla/5.0"}
_ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt":   "http://www.youtube.com/xml/schemas/2015",
}
# YouTube's feed endpoint is intermittently throttled (spurious 404/500), so a
# single blip must not drop the whole aisearch category — retry with backoff.
RSS_RETRY_ATTEMPTS = 3
RSS_RETRY_BACKOFF = 2.0

# Chapters with these titles are navigation-only — skip them in story output
SKIP_CHAPTER_TITLES = {"intro", "ai news intro", "introduction", "outro", "credits", "sponsor"}


# ── RSS + yt-dlp ───────────────────────────────────────────────────────────────

def _fetch_rss(url: str, timeout: int = 10) -> bytes:
    """Fetch raw RSS bytes (isolated so it can be swapped for a fixture in tests)."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _parse_latest(xml_bytes: bytes) -> tuple[str, str]:
    """Return (url, title) of the newest entry in an Atom feed body."""
    root = ET.fromstring(xml_bytes)
    entries = root.findall(".//atom:entry", _ATOM_NS)
    if not entries:
        raise RuntimeError("No entries found in RSS feed")
    first = entries[0]
    video_id = first.find("yt:videoId", _ATOM_NS).text
    title    = first.find("atom:title",  _ATOM_NS).text
    return f"https://www.youtube.com/watch?v={video_id}", title


def _parse_ytdlp_flat(info: dict) -> tuple[str, str]:
    """Return (url, title) of the newest entry in a yt-dlp flat channel listing."""
    entries = info.get("entries") or []
    if not entries:
        raise RuntimeError("yt-dlp channel listing returned no entries")
    first = entries[0]
    video_id = first.get("id")
    url = first.get("url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else "")
    if not url:
        raise RuntimeError("yt-dlp entry missing both url and id")
    return url, first.get("title") or ""


def _latest_via_ytdlp() -> tuple[str, str]:
    """Fallback: newest upload via yt-dlp's flat channel listing.

    Uses YouTube's web/innertube API — a different endpoint than the /feeds RSS,
    so it stays reachable when the RSS endpoint is IP-throttled (spurious
    404/500). Isolated so tests can inject a fixture-backed parser instead.
    """
    import yt_dlp
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlistend": 1,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(CHANNEL_VIDEOS, download=False)
    return _parse_ytdlp_flat(info)


def get_latest_video_url(
    *,
    fetch=_fetch_rss,
    attempts: int = RSS_RETRY_ATTEMPTS,
    backoff: float = RSS_RETRY_BACKOFF,
    sleep=time.sleep,
    fallback=_latest_via_ytdlp,
) -> tuple[str, str]:
    """Return (url, title) of the most recent theAIsearch upload.

    Tries the RSS feed first, retrying transient failures (HTTP 404/500,
    timeouts, malformed/empty bodies) with linear backoff. If RSS is exhausted —
    typically a sustained /feeds throttle rather than a blip — it falls back to
    ``fallback`` (yt-dlp on a different endpoint) so the aisearch category
    survives. ``fetch``/``sleep``/``fallback`` are seams for fixture-backed tests.
    """
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _parse_latest(fetch(CHANNEL_RSS))
        except (urllib.error.URLError, ET.ParseError, RuntimeError) as exc:
            last_exc = exc
            if attempt < attempts:
                sleep(backoff * attempt)
    if fallback is not None:
        try:
            url, title = fallback()
            print("  aisearch: RSS throttled — recovered via yt-dlp fallback", file=sys.stderr)
            return url, title
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise RuntimeError(
        f"theAIsearch RSS+fallback failed after {attempts} attempts: {last_exc}"
    )


def _fetch_via_python_module(url: str) -> dict:
    import yt_dlp
    opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "url":         url,
        "title":       info.get("title", ""),
        "upload_date": info.get("upload_date", ""),
        "description": info.get("description", ""),
        "chapters":    info.get("chapters") or [],
    }


def _fetch_via_cli(url: str) -> dict:
    import subprocess
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-playlist", "--quiet", url],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp CLI failed: {result.stderr[:200]}")
    data = json.loads(result.stdout)
    return {
        "url":         url,
        "title":       data.get("title", ""),
        "upload_date": data.get("upload_date", ""),
        "description": data.get("description", ""),
        "chapters":    data.get("chapters") or [],
    }


def fetch_video_info(url: str) -> dict:
    """Try Python module first, fall back to CLI."""
    for fetcher, label in [(_fetch_via_python_module, "yt_dlp module"),
                            (_fetch_via_cli,           "yt-dlp CLI")]:
        try:
            info = fetcher(url)
            print(f"  Fetched via {label}", file=sys.stderr)
            return info
        except Exception as e:
            print(f"  {label} failed: {e}", file=sys.stderr)
    raise RuntimeError("Both yt-dlp module and CLI failed — is yt-dlp installed?")


# ── Story-card conversion ──────────────────────────────────────────────────────

def _chapter_url(video_url: str, start_time: float) -> str:
    """YouTube deep-link to a specific timestamp."""
    t = int(start_time)
    base = video_url.split("&t=")[0]  # strip existing timestamp if any
    return f"{base}&t={t}s"


def to_story_cards(info: dict) -> list[dict]:
    """
    Convert video chapters to story-card dicts.
    Rule: include EVERY chapter except navigation-only ones (intro/outro).
    """
    chapters = info.get("chapters") or []
    video_url = info.get("url", "")
    stories = []

    for ch in chapters:
        title = ch.get("title", "").strip()
        if title.lower() in SKIP_CHAPTER_TITLES:
            continue
        start = ch.get("start_time", 0)
        url   = _chapter_url(video_url, start) if video_url else video_url
        stories.append(make_story(
            title, url, "theAIsearch",
            raw_snippet=f"theAIsearch video chapter @ {int(start)//60}:{int(start)%60:02d}",
        ))

    return stories


def fetch_stories(url: str | None = None) -> dict:
    """Return a category envelope ready to embed in the partial digest JSON."""
    if url is None:
        url, _ = get_latest_video_url()
    info = fetch_video_info(url)
    return make_category("aisearch", to_story_cards(info))


# ── Human-readable printer ─────────────────────────────────────────────────────

def print_chapters(info: dict) -> None:
    print(f"\n📺  {info['title']}")
    print(f"🔗  {info['url']}")
    if info.get("upload_date"):
        d = info["upload_date"]
        print(f"📅  {d[:4]}-{d[4:6]}-{d[6:]}")
    print()
    chapters = info.get("chapters") or []
    if chapters:
        print(f"Chapters ({len(chapters)}):")
        for ch in chapters:
            m, s = divmod(int(ch["start_time"]), 60)
            print(f"  {m:>3}:{s:02d}  {ch['title']}")
    else:
        print("No chapters found — description:\n")
        print(info.get("description", ""))


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fetch theAIsearch YouTube chapter list")
    parser.add_argument("--url", help="Specific video URL (default: latest from RSS)")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--stories", action="store_true",
                      help="Output story-card JSON (for digest merging)")
    mode.add_argument("--json", action="store_true", dest="raw_json",
                      help="Output raw video metadata + chapters as JSON")
    args = parser.parse_args()

    if args.url:
        url = args.url
    else:
        print("Fetching latest video from RSS…", file=sys.stderr)
        url, rss_title = get_latest_video_url()
        print(f"Latest: {rss_title}", file=sys.stderr)

    info = fetch_video_info(url)

    if args.stories:
        print(json.dumps(fetch_stories.__wrapped__(info)
                         if hasattr(fetch_stories, "__wrapped__") else
                         make_category("aisearch", to_story_cards(info)),
                         indent=2, ensure_ascii=False))
        return

    if args.raw_json:
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return

    print_chapters(info)


if __name__ == "__main__":
    main()
