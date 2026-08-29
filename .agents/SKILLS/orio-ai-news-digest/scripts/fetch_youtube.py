"""
General-purpose YouTube channel + transcript fetcher.

Works for ANY YouTube channel. Fetches recent videos via RSS, extracts
chapters and full transcripts using yt-dlp (always installed) and
youtube-transcript-api (optional, for cleaner captions).

Fails LOUDLY — no silent fallbacks. Every error prints a clear message
and exits non-zero so callers and Claude know something went wrong.

Usage
-----
# Latest video from theAIsearch (chapters + transcript)
python fetch_youtube.py --channel UCIgnGlGkVRhd4qNFcEwLL4A

# Any channel by URL
python fetch_youtube.py --channel https://www.youtube.com/@MattWolfe

# Specific video
python fetch_youtube.py --url https://www.youtube.com/watch?v=s3rNDndvav0

# Last 3 videos from a channel
python fetch_youtube.py --channel UCIgnGlGkVRhd4qNFcEwLL4A --recent 3

# Output modes
--chapters        Print chapter list (default)
--transcript      Print full transcript text
--stories         Output story-card JSON (for digest merging)
--json            Output raw metadata + chapters + transcript as JSON

# Save output
python fetch_youtube.py --channel ... --transcript --out transcript.txt

Requires: pip install yt-dlp
Optional: pip install youtube-transcript-api   (cleaner captions)
"""

import argparse
import json
import re
import sys
import textwrap
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _cache_utils import cache_write, cache_read, cache_stale, build_prefix, cache_path

# ── Constants ──────────────────────────────────────────────────────────────────

HEADERS = {"User-Agent": "Mozilla/5.0"}

# Well-known channel IDs for convenience
KNOWN_CHANNELS = {
    "theaisearch":    "UCIgnGlGkVRhd4qNFcEwLL4A",
    "mattwolfe":      "UCXIJgqnII2ZOINSWNf17zhA",
    "yannickilcher":  "UCZHmQk67mSJgfCCTn7xBfew",
    "twopapers":      "UCbfYPyITQ-7l4upoX8nvctg",
    "theaigrid":      "UCF6sZyo3yKkGzPmkWl8csmQ",
}

SKIP_CHAPTER_TITLES = {"intro", "ai news intro", "introduction", "outro", "credits"}


# ── Errors ─────────────────────────────────────────────────────────────────────

def die(msg: str, code: int = 1) -> None:
    """Print a loud error and exit. Never suppress this."""
    print(f"\n❌  ERROR: {msg}", file=sys.stderr)
    print("    (script exiting non-zero — caller must handle this)", file=sys.stderr)
    sys.exit(code)


def warn(msg: str) -> None:
    print(f"⚠️   WARNING: {msg}", file=sys.stderr)


# ── Channel ID resolution ──────────────────────────────────────────────────────

def resolve_channel_id(channel: str) -> str:
    """
    Accept: channel ID, handle (@name), full URL, or known alias.
    Returns a bare channel ID (UCxxxxxxxx) or dies with a clear message.
    """
    # Known alias
    if channel.lower() in KNOWN_CHANNELS:
        return KNOWN_CHANNELS[channel.lower()]

    # Already a bare channel ID
    if re.match(r"^UC[a-zA-Z0-9_-]{22}$", channel):
        return channel

    # Extract from URL patterns
    patterns = [
        r"youtube\.com/channel/(UC[a-zA-Z0-9_-]{22})",
        r"youtube\.com/c/([^/?&]+)",
        r"youtube\.com/@([^/?&]+)",
    ]
    for pat in patterns:
        m = re.search(pat, channel)
        if m:
            candidate = m.group(1)
            # If it looks like a channel ID, use it directly
            if re.match(r"^UC[a-zA-Z0-9_-]{22}$", candidate):
                return candidate
            # Otherwise it's a handle — resolve via RSS search
            return _resolve_handle(candidate)

    die(
        f"Cannot resolve channel: {channel!r}\n"
        "    Provide a UC... channel ID, a @handle URL, or a known alias:\n"
        f"    {list(KNOWN_CHANNELS.keys())}"
    )


def _resolve_handle(handle: str) -> str:
    """Resolve a @handle to a channel ID by fetching the channel page."""
    url = f"https://www.youtube.com/@{handle}"
    print(f"  Resolving @{handle} → channel ID…", file=sys.stderr)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(r'"channelId"\s*:\s*"(UC[a-zA-Z0-9_-]{22})"', html)
        if not m:
            m = re.search(r'channel/(UC[a-zA-Z0-9_-]{22})', html)
        if m:
            cid = m.group(1)
            print(f"  Resolved: {cid}", file=sys.stderr)
            return cid
        die(f"Could not find channel ID for @{handle}. The page may require JS rendering.")
    except Exception as e:
        die(f"Failed to resolve @{handle}: {e}")


# ── RSS feed ───────────────────────────────────────────────────────────────────

def get_recent_videos(channel_id: str, n: int = 1) -> list[dict]:
    """
    Fetch the N most recent videos from a channel via RSS.
    Returns list of {url, title, published}.
    Dies if the feed is empty or unreachable.
    """
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    print(f"  Fetching RSS: {rss_url}", file=sys.stderr)
    try:
        req = urllib.request.Request(rss_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            tree = ET.parse(resp)
    except Exception as e:
        die(f"RSS fetch failed for channel {channel_id}: {e}\n"
            "    Check that the channel ID is correct and the network is reachable.")

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt":   "http://www.youtube.com/xml/schemas/2015",
    }
    entries = tree.findall(".//atom:entry", ns)
    if not entries:
        die(f"RSS feed returned 0 entries for channel {channel_id}. "
            "The channel may be private, empty, or the ID is wrong.")

    results = []
    for entry in entries[:n]:
        video_id  = entry.find("yt:videoId", ns).text
        title_el  = entry.find("atom:title",     ns)
        pub_el    = entry.find("atom:published",  ns)
        results.append({
            "url":       f"https://www.youtube.com/watch?v={video_id}",
            "title":     title_el.text  if title_el  is not None else "",
            "published": pub_el.text    if pub_el    is not None else "",
        })

    print(f"  Found {len(entries)} videos in feed, returning {len(results)}", file=sys.stderr)
    return results


# ── Video metadata + chapters via yt-dlp ──────────────────────────────────────

def fetch_video_info(url: str) -> dict:
    """
    Fetch full video metadata (title, chapters, description) via yt-dlp.
    Tries Python module first, then CLI. Dies if both fail.
    """
    info = _try_yt_dlp_module(url) or _try_yt_dlp_cli(url)
    if info is None:
        die(
            f"yt-dlp could not fetch metadata for {url}\n"
            "    Make sure yt-dlp is installed: pip install yt-dlp\n"
            "    Try running manually: yt-dlp --dump-json --no-playlist --quiet <URL>"
        )
    chapters = info.get("chapters") or []
    if not chapters:
        warn(f"No chapters found in video: {url}\n"
             "    The video may not have chapter markers. "
             "Use --transcript to get the full narration instead.")
    return info


def _try_yt_dlp_module(url: str) -> dict | None:
    try:
        import yt_dlp
        opts = {"quiet": True, "skip_download": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            raw = ydl.extract_info(url, download=False)
        print("  Metadata fetched via yt_dlp module", file=sys.stderr)
        return _normalise(raw, url)
    except ImportError:
        warn("yt_dlp Python module not installed — trying CLI")
        return None
    except Exception as e:
        warn(f"yt_dlp module failed: {e}")
        return None


def _try_yt_dlp_cli(url: str) -> dict | None:
    import subprocess
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", "--quiet", url],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            warn(f"yt-dlp CLI exit {result.returncode}: {result.stderr[:300]}")
            return None
        raw = json.loads(result.stdout)
        print("  Metadata fetched via yt-dlp CLI", file=sys.stderr)
        return _normalise(raw, url)
    except FileNotFoundError:
        warn("yt-dlp CLI not found in PATH")
        return None
    except Exception as e:
        warn(f"yt-dlp CLI failed: {e}")
        return None


def _normalise(raw: dict, url: str) -> dict:
    return {
        "url":         url,
        "title":       raw.get("title", ""),
        "upload_date": raw.get("upload_date", ""),
        "description": raw.get("description", ""),
        "chapters":    raw.get("chapters") or [],
        "duration":    raw.get("duration", 0),
        "view_count":  raw.get("view_count", 0),
    }


# ── Transcript fetching ────────────────────────────────────────────────────────

def fetch_transcript(url: str, lang: str = "en") -> str:
    """
    Fetch the full spoken transcript of a YouTube video.
    Tries youtube-transcript-api first (clean), then yt-dlp subtitle download.
    Dies if neither works and reports exactly why.
    """
    video_id = _extract_video_id(url)
    if not video_id:
        die(f"Cannot extract video ID from URL: {url}")

    transcript = _transcript_via_api(video_id, lang)
    if transcript:
        return transcript

    transcript = _transcript_via_ytdlp(url, lang)
    if transcript:
        return transcript

    die(
        f"Could not fetch transcript for {url}\n"
        "    Tried: youtube-transcript-api, yt-dlp subtitle download\n"
        "    Possible reasons:\n"
        "      - Subtitles are disabled for this video\n"
        "      - The video is private or age-restricted\n"
        "      - No English captions available (try --lang LANGCODE)\n"
        "    Install: pip install youtube-transcript-api"
    )


def _extract_video_id(url: str) -> str | None:
    m = re.search(r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else None


def _transcript_via_api(video_id: str, lang: str) -> str | None:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
        try:
            segments = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang, f"{lang}-US", "en", "en-US"])
            print(f"  Transcript fetched via youtube-transcript-api ({len(segments)} segments)", file=sys.stderr)
            return " ".join(s["text"] for s in segments)
        except (NoTranscriptFound, TranscriptsDisabled) as e:
            warn(f"youtube-transcript-api: {e}")
            return None
    except ImportError:
        warn("youtube-transcript-api not installed (pip install youtube-transcript-api) — trying yt-dlp")
        return None
    except Exception as e:
        warn(f"youtube-transcript-api unexpected error: {e}")
        return None


def _transcript_via_ytdlp(url: str, lang: str) -> str | None:
    import subprocess, tempfile, glob, os
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                "yt-dlp",
                "--write-auto-sub", "--write-sub",
                "--sub-lang", f"{lang},{lang}-US,en,en-US",
                "--sub-format", "vtt",
                "--skip-download",
                "--no-playlist",
                "--quiet",
                "-o", f"{tmpdir}/sub",
                url,
            ],
            capture_output=True, text=True, timeout=60,
        )
        vtt_files = glob.glob(f"{tmpdir}/*.vtt")
        if not vtt_files:
            if result.returncode != 0:
                warn(f"yt-dlp subtitle download failed: {result.stderr[:300]}")
            else:
                warn("yt-dlp ran OK but no .vtt files written — subtitles may not be available")
            return None

        text = _parse_vtt(vtt_files[0])
        print(f"  Transcript fetched via yt-dlp subtitles ({len(text)} chars)", file=sys.stderr)
        return text


def _parse_vtt(path: str) -> str:
    """Parse a WebVTT file into plain text, deduplicating overlapping captions."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    # Strip WebVTT header, timestamps, and tags
    lines = []
    for line in raw.splitlines():
        if re.match(r"^\d{2}:\d{2}", line) or line.startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        clean = re.sub(r"<[^>]+>", "", line).strip()
        if clean and clean not in {"", "align:start position:0%"}:
            lines.append(clean)
    # Deduplicate consecutive repeated lines (common in auto-subs)
    deduped = []
    for line in lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)
    return " ".join(deduped)


# ── Story-card helpers ─────────────────────────────────────────────────────────

def _chapter_url(video_url: str, start_time: float) -> str:
    base = video_url.split("&t=")[0]
    return f"{base}&t={int(start_time)}s"


def chapters_to_stories(info: dict, include_sponsor: bool = False) -> list[dict]:
    """
    One story card per chapter. Never filters content chapters.
    Sponsor chapters are excluded by default (pass include_sponsor=True to keep).
    """
    sponsor_keywords = {"sponsor", "ad", "advertisement"} if not include_sponsor else set()
    stories = []
    for ch in info.get("chapters") or []:
        title = ch.get("title", "").strip()
        if not title:
            continue
        if title.lower() in SKIP_CHAPTER_TITLES:
            continue
        if any(kw in title.lower() for kw in sponsor_keywords):
            continue
        start = ch.get("start_time", 0)
        stories.append({
            "id":               re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
            "title":            title,
            "summary":          "",  # Claude fills this in from transcript context
            "source":           "theAIsearch",
            "url":              _chapter_url(info["url"], start),
            "significance":     0,   # Claude scores this
            "novelty":          0,
            "relevance_design": 0,
            "tags":             [],
            "image_url":        None,
            "chapter_time":     f"{int(start)//60}:{int(start)%60:02d}",
        })
    return stories


# ── Output formatters ──────────────────────────────────────────────────────────

def print_chapters(info: dict) -> None:
    print(f"\n📺  {info['title']}")
    print(f"🔗  {info['url']}")
    d = info.get("upload_date", "")
    if d:
        print(f"📅  {d[:4]}-{d[4:6]}-{d[6:]}")
    print(f"👁   {info.get('view_count', 0):,} views")
    chapters = info.get("chapters") or []
    if chapters:
        print(f"\nChapters ({len(chapters)}):")
        for ch in chapters:
            m, s = divmod(int(ch["start_time"]), 60)
            print(f"  {m:>3}:{s:02d}  {ch['title']}")
    else:
        print("\n⚠️  No chapter markers found in this video.")
        print("    Use --transcript to get the full narration text.")


def print_transcript(text: str, wrap: int = 100) -> None:
    print("\n── TRANSCRIPT ─────────────────────────────────────────────────────\n")
    for para in textwrap.wrap(text, width=wrap):
        print(para)
    print(f"\n── END ({len(text.split())} words) ────────────────────────────────")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch YouTube channel videos, chapters, and transcripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--channel", metavar="CHANNEL",
                     help="Channel ID, @handle URL, or alias (e.g. theaisearch)")
    src.add_argument("--url", metavar="URL",
                     help="Specific video URL")

    parser.add_argument("--recent", type=int, default=1, metavar="N",
                        help="How many recent videos to fetch (default: 1, requires --channel)")
    parser.add_argument("--transcript", action="store_true",
                        help="Fetch and print the full spoken transcript")
    parser.add_argument("--lang", default="en", metavar="LANG",
                        help="Transcript language code (default: en)")
    parser.add_argument("--include-sponsor", action="store_true",
                        help="Include sponsor chapters in --stories output")
    parser.add_argument("--out", metavar="FILE",
                        help="Write output to FILE instead of stdout")
    parser.add_argument("--prefix", metavar="PREFIX",
                        help="14-digit digest prefix for cache naming (default: today noon UTC)")
    parser.add_argument("--cache", action="store_true", default=True,
                        help="Write output to .cache/PREFIX_fetch_youtube.json (default: on)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Skip reading and writing the cache")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch even if a fresh cache file exists")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--chapters", action="store_true",
                      help="Print chapter list (default)")
    mode.add_argument("--stories", action="store_true",
                      help="Output story-card JSON for digest merging")
    mode.add_argument("--json", action="store_true", dest="raw_json",
                      help="Output full metadata as JSON")

    args = parser.parse_args()

    if args.recent > 1 and args.url:
        die("--recent requires --channel, not --url")

    use_cache = not args.no_cache
    prefix    = args.prefix or build_prefix()

    # Check cache first (unless --force or --no-cache)
    if use_cache and not args.force and (args.stories or args.raw_json):
        cached = cache_read(prefix, "fetch_youtube")
        if cached is not None:
            out_text = json.dumps(cached, indent=2, ensure_ascii=False)
            if args.out:
                Path(args.out).write_text(out_text, encoding="utf-8")
                print(f"\n✅  (from cache) Written to {args.out}", file=sys.stderr)
            else:
                print(out_text)
            print("\n✅  Done (cache hit).", file=sys.stderr)
            return

    # Resolve video URLs
    if args.url:
        video_urls = [{"url": args.url, "title": "", "published": ""}]
    else:
        channel_id = resolve_channel_id(args.channel)
        video_urls = get_recent_videos(channel_id, n=args.recent)

    all_output = []

    for entry in video_urls:
        url = entry["url"]
        print(f"\n── Processing: {url}", file=sys.stderr)

        info = fetch_video_info(url)
        # Enrich with RSS title if yt-dlp title is empty
        if not info["title"] and entry.get("title"):
            info["title"] = entry["title"]

        transcript_text = None
        if args.transcript or args.stories:
            transcript_text = fetch_transcript(url, lang=args.lang)
            info["transcript"] = transcript_text

        if args.raw_json:
            all_output.append(info)
        elif args.stories:
            stories = chapters_to_stories(info, include_sponsor=args.include_sponsor)
            if not stories:
                warn(f"No story cards generated for {url} — no chapters found.\n"
                     "    The digest AI Search category will be empty for this video.\n"
                     "    Use --transcript to get the narration and create stories manually.")
            all_output.append({
                "video_url":   url,
                "video_label": info["title"],
                "category":    "aisearch",
                "stories":     stories,
                "transcript":  transcript_text or "",
            })
        else:
            # Default: print chapters (and transcript if requested)
            print_chapters(info)
            if args.transcript and transcript_text:
                print_transcript(transcript_text)
            continue  # don't add to all_output for text mode

    # Serialise JSON modes
    if args.raw_json or args.stories:
        payload = all_output if len(all_output) > 1 else all_output[0]
        out_text = json.dumps(payload, indent=2, ensure_ascii=False)

        # Write to cache
        if use_cache:
            cache_write(payload, prefix, "fetch_youtube")

        if args.out:
            Path(args.out).write_text(out_text, encoding="utf-8")
            print(f"\n✅  Written to {args.out}", file=sys.stderr)
        else:
            print(out_text)

    elif args.transcript and transcript_text and args.out:
        Path(args.out).write_text(transcript_text, encoding="utf-8")
        print(f"\n✅  Transcript written to {args.out}", file=sys.stderr)

    print("\n✅  Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
