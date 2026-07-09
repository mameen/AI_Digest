"""
Multi-channel YouTube ingest: secondary creators (wide net).

Each channel's latest accessible video is fetched via yt-dlp. Topics come from
chapters when present, else timestamp lines in the description, else the whole
video as a single topic. Descriptions are always retained for enrich/grounding.
"""

from __future__ import annotations

import re
import sys
import time
import xml.etree.ElementTree as ET
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from _story_utils import make_category, make_story
from link_extract import (
    description_segment,
    extract_links_from_text,
    order_story_links,
    parse_description_resources,
)

_MEMBERS_ONLY = re.compile(r"members-only|join this channel", re.I)
_ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}
RSS_RETRY_ATTEMPTS = 3
RSS_RETRY_BACKOFF = 2.0

SKIP_CHAPTER_TITLES = {
    "intro",
    "ai news intro",
    "introduction",
    "outro",
    "credits",
    "sponsor",
    "timestamps",
    "timestamps.",
}

# Secondary channels (theAIsearch stays on the dedicated aisearch category).
SECONDARY_CHANNELS: list[dict[str, str]] = [
    {
        "key": "ibm-technology",
        "label": "IBM Technology",
        "handle": "https://www.youtube.com/@IBMTechnology",
        "channel_id": "UCKWaEZ-_VweaEx1j62do_vQ",
    },
    {
        "key": "google-cloud-tech",
        "label": "Google Cloud Tech",
        "handle": "https://www.youtube.com/@googlecloudtech",
        "channel_id": "UCJS9pqu9BzkAMNTmzNMNhvg",
    },
    {
        "key": "the-stack-ai",
        "label": "The Stack",
        "handle": "https://www.youtube.com/@The-Stack-ai",
        "channel_id": "UCjete_rlEo4zKvkzJNCMzsA",
    },
    {
        "key": "nate-herk",
        "label": "Nate Herk",
        "handle": "https://www.youtube.com/@nateherk",
        "channel_id": "UC2ojq-nuP8ceeHqiroeKhBA",
    },
    {
        "key": "network-chuck",
        "label": "NetworkChuck",
        "handle": "https://www.youtube.com/@NetworkChuck",
        "channel_id": "UC9x0AN7BWHpCDHSm9NiJFJQ",
    },
    {
        "key": "azisk",
        "label": "Alex Ziskind",
        "handle": "https://www.youtube.com/@AZisk",
        "channel_id": "UCajiMK_CY9icRhLepS8_3ug",
    },
    {
        "key": "hugging-face",
        "label": "Hugging Face",
        "handle": "https://www.youtube.com/@HuggingFace",
        "channel_id": "UCHlNU7kIZhRgSbhHvFoy72w",
    },
    {
        "key": "bytebyteai",
        "label": "ByteByteAI",
        "handle": "https://www.youtube.com/channel/UC5mEvNHnfRNuDivuXiCPiZA",
        "channel_id": "UC5mEvNHnfRNuDivuXiCPiZA",
    },
    {
        "key": "bytebytego",
        "label": "ByteByteGo",
        "handle": "https://www.youtube.com/channel/UCZgt6AzoyjslHTC9dz0UoTw",
        "channel_id": "UCZgt6AzoyjslHTC9dz0UoTw",
    },
    {
        "key": "full-stack",
        "label": "Full Stack",
        "handle": "https://www.youtube.com/@full_stackYT",
        "channel_id": "UC_GBIzXUzVTV9r7GKpu6IWw",
    },
]

_TIMESTAMP_LINE = re.compile(
    r"^\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s+(.+?)\s*$",
    re.MULTILINE,
)

HEADERS = {"User-Agent": "Mozilla/5.0"}

_STOP_WORDS = frozenset(
    {"the", "a", "an", "with", "and", "or", "to", "for", "of", "in", "on", "everything"}
)
# (resource name hints, topic title hints) — boosts chapter ↔ tool matching.
_TOPIC_RESOURCE_HINTS: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("gemini", "cli"), ("gemini", "frontier", "card", "free")),
    (("aider",), ("aider", "commit", "git", "auto")),
    (("opencode",), ("opencode", "terminal", "test", "writes", "agent", "lsp")),
    (("cc-switch", "cc switch", "router", "musistudio"), ("gui", "rule", "window")),
    (("claw", "claude code"), ("leaked", "100k", "codebase", "stars")),
    (("ecc", "everything claude"), ("security", "layer", "ships", "scanner")),
]


def _fetch_rss(url: str, timeout: int = 10) -> bytes:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _parse_latest_rss(xml_bytes: bytes) -> tuple[str, str]:
    root = ET.fromstring(xml_bytes)
    entries = root.findall(".//atom:entry", _ATOM_NS)
    if not entries:
        raise RuntimeError("No entries found in RSS feed")
    first = entries[0]
    video_id = first.find("yt:videoId", _ATOM_NS).text
    title = first.find("atom:title", _ATOM_NS).text
    return f"https://www.youtube.com/watch?v={video_id}", title or ""


def _parse_ytdlp_flat(info: dict) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for ent in info.get("entries") or []:
        video_id = ent.get("id")
        url = ent.get("url") or (
            f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
        )
        if url:
            out.append((url, ent.get("title") or ""))
    if not out:
        raise RuntimeError("yt-dlp channel listing returned no entries")
    return out


def _latest_listing_via_ytdlp(videos_url: str, *, playlistend: int = 3) -> list[tuple[str, str]]:
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "playlistend": playlistend,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(videos_url, download=False)
    return _parse_ytdlp_flat(info)


def get_latest_video_listing(
    channel: dict[str, str],
    *,
    fetch: Callable[[str], bytes] = _fetch_rss,
    attempts: int = RSS_RETRY_ATTEMPTS,
    backoff: float = RSS_RETRY_BACKOFF,
    sleep: Callable[[float], None] = time.sleep,
    listing_fallback: Callable[[str], list[tuple[str, str]]] | None = None,
    playlistend: int = 3,
) -> list[tuple[str, str]]:
    """Return up to ``playlistend`` recent (url, title) pairs for a channel."""
    rss = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel['channel_id']}"
    videos_url = f"{channel['handle'].rstrip('/')}/videos"
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return [_parse_latest_rss(fetch(rss))]
        except (urllib.error.URLError, ET.ParseError, RuntimeError) as exc:
            last_exc = exc
            if attempt < attempts:
                sleep(backoff * attempt)
    fallback = listing_fallback or (
        lambda url: _latest_listing_via_ytdlp(url, playlistend=playlistend)
    )
    try:
        listing = fallback(videos_url)
        print(
            f"  youtube/{channel['key']}: RSS throttled — recovered via yt-dlp",
            file=sys.stderr,
        )
        return listing
    except Exception as exc:  # noqa: BLE001
        last_exc = exc
    raise RuntimeError(
        f"{channel['label']} RSS+fallback failed after {attempts} attempts: {last_exc}"
    )


def _fetch_via_python_module(url: str) -> dict:
    import yt_dlp

    opts = {"quiet": True, "skip_download": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return _normalize_video_info(url, info)


def _fetch_via_cli(url: str) -> dict:
    import json
    import subprocess

    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-playlist", "--quiet", url],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp CLI failed: {result.stderr[:200]}")
    data = json.loads(result.stdout)
    return _normalize_video_info(url, data)


def _normalize_video_info(url: str, info: dict) -> dict:
    return {
        "url": url,
        "title": info.get("title", ""),
        "upload_date": info.get("upload_date", ""),
        "description": info.get("description", ""),
        "chapters": info.get("chapters") or [],
    }


def fetch_video_info(url: str) -> dict:
    """Try Python yt-dlp module first, fall back to CLI."""
    last_error: Exception | None = None
    for fetcher, label in [(_fetch_via_python_module, "yt_dlp module"), (_fetch_via_cli, "yt-dlp CLI")]:
        try:
            info = fetcher(url)
            print(f"  Fetched via {label}", file=sys.stderr)
            return info
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"  {label} failed: {exc}", file=sys.stderr)
    raise RuntimeError(f"Both yt-dlp module and CLI failed: {last_error}")


def is_members_only_error(exc: BaseException) -> bool:
    return bool(_MEMBERS_ONLY.search(str(exc)))


def chapter_url(video_url: str, start_time: float) -> str:
    t = int(start_time)
    base = video_url.split("&t=")[0]
    return f"{base}&t={t}s"


def _timestamp_to_seconds(hours: str | None, minutes: str, seconds: str) -> int:
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds)


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _score_resource_topic(
    topic_title: str,
    resource_name: str,
    *,
    segment: str = "",
) -> int:
    t = _normalize_text(topic_title)
    r = _normalize_text(resource_name)
    seg = _normalize_text(segment)
    r_tokens = set(r.split()) - _STOP_WORDS
    t_tokens = set(t.split()) - _STOP_WORDS
    score = len(r_tokens & t_tokens) * 2
    for res_keys, topic_keys in _TOPIC_RESOURCE_HINTS:
        if any(k in r for k in res_keys):
            matches = sum(1 for k in topic_keys if k in t)
            score += matches * 3
    if seg and r_tokens:
        if any(len(tok) > 3 and tok in seg for tok in r_tokens):
            score += 4
    return score


def match_resources_to_topics(
    topics: list[dict[str, Any]],
    resources: list[dict[str, str]],
    description: str = "",
) -> dict[str, list[dict[str, str]]]:
    """Map chapter/topic title → resource links (best match per tool)."""
    if not topics or not resources:
        return {}
    ordered = sorted(topics, key=lambda t: int(t.get("start_s") or 0))
    mapping: dict[str, list[dict[str, str]]] = {t["title"]: [] for t in ordered}
    assigned: set[str] = set()

    for res in resources:
        best_title = ""
        best_score = 0
        for i, topic in enumerate(ordered):
            start = int(topic.get("start_s") or 0)
            nxt = int(ordered[i + 1]["start_s"]) if i + 1 < len(ordered) else None
            segment = description_segment(description, start, nxt)
            score = _score_resource_topic(topic["title"], res["name"], segment=segment)
            if score > best_score:
                best_score = score
                best_title = topic["title"]
        if best_title and best_score >= 2 and res["url"] not in assigned:
            mapping[best_title].append(res)
            assigned.add(res["url"])
    return mapping


def attach_story_links(
    stories: list[dict[str, Any]],
    topics: list[dict[str, Any]],
    description: str,
) -> None:
    """Stamp ``links[]``: all description links; chapter/tool matches first (in-place)."""
    if not description:
        return
    tool_resources = parse_description_resources(description)
    desc_links = extract_links_from_text(description, allow_named_product_urls=True)
    all_resources = order_story_links(tool_resources, desc_links)
    by_title = match_resources_to_topics(topics, tool_resources, description) if tool_resources else {}
    ordered_topics = sorted(topics, key=lambda t: int(t.get("start_s") or 0))

    for story in stories:
        key = story.get("topic") or story.get("title") or ""
        primary = list(by_title.get(key) or [])
        idx = next((i for i, t in enumerate(ordered_topics) if t["title"] == key), None)
        if idx is not None:
            start = int(ordered_topics[idx].get("start_s") or 0)
            nxt = (
                int(ordered_topics[idx + 1]["start_s"])
                if idx + 1 < len(ordered_topics)
                else None
            )
            seg = description_segment(description, start, nxt)
            seg_links = extract_links_from_text(
                seg, exclude_urls={story.get("url") or ""}, allow_named_product_urls=True
            )
            primary = order_story_links(primary, seg_links)
        story["links"] = order_story_links(
            primary,
            all_resources,
        )


def reattach_links_to_youtube_category(cat: dict[str, Any]) -> None:
    """Re-apply link attachment from ``sources[]`` (e.g. after preflight patch)."""
    sources = {s["channel_key"]: s for s in cat.get("sources") or [] if s.get("channel_key")}
    for ck, src in sources.items():
        batch = [s for s in cat.get("stories") or [] if s.get("channel_key") == ck]
        attach_story_links(batch, src.get("topics") or [], src.get("description") or "")


def parse_description_timestamps(description: str) -> list[dict[str, Any]]:
    """Parse ``MM:SS title`` / ``H:MM:SS title`` lines from a video description."""
    topics: list[dict[str, Any]] = []
    for match in _TIMESTAMP_LINE.finditer(description or ""):
        hours, minutes, seconds, title = match.groups()
        title = title.strip()
        low = title.lower()
        if not title or low in SKIP_CHAPTER_TITLES:
            continue
        if title.startswith("http"):
            continue
        topics.append(
            {
                "title": title,
                "start_s": _timestamp_to_seconds(hours, minutes, seconds),
            }
        )
    return topics


def extract_topics(info: dict[str, Any]) -> list[dict[str, Any]]:
    """Topics from chapters, description timestamps, or the whole video."""
    video_url = info.get("url") or ""
    chapters = info.get("chapters") or []
    topics: list[dict[str, Any]] = []

    if chapters:
        for ch in chapters:
            title = (ch.get("title") or "").strip()
            if title.lower() in SKIP_CHAPTER_TITLES:
                continue
            start = float(ch.get("start_time") or 0)
            topics.append({"title": title, "start_s": int(start), "origin": "chapter"})
        if topics:
            return topics

    desc_topics = parse_description_timestamps(info.get("description") or "")
    if desc_topics:
        for t in desc_topics:
            t["origin"] = "description"
        return desc_topics

    title = (info.get("title") or "Latest video").strip()
    return [{"title": title, "start_s": 0, "origin": "video"}]


def topics_to_story_cards(
    info: dict[str, Any],
    *,
    channel_key: str,
    channel_label: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (topic metadata list, story cards)."""
    video_url = info.get("url") or ""
    topic_rows = extract_topics(info)
    topics: list[dict[str, Any]] = []
    stories: list[dict[str, Any]] = []

    for topic in topic_rows:
        start = int(topic.get("start_s") or 0)
        title = topic["title"]
        url = chapter_url(video_url, start) if video_url else video_url
        m, s = divmod(start, 60)
        h, m = divmod(m, 60)
        stamp = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        topics.append({"title": title, "url": url, "start_s": start, "origin": topic.get("origin")})
        stories.append(
            make_story(
                title,
                url,
                channel_label,
                id_prefix=f"yt-{channel_key}",
                raw_snippet=f"{channel_label} @ {stamp} — {info.get('title', '')}",
                extra_tags=["youtube"],
            )
            | {
                "channel_key": channel_key,
                "channel_label": channel_label,
                "topic": title,
            }
        )
    attach_story_links(stories, topic_rows, info.get("description") or "")
    return topics, stories


def fetch_accessible_video_info(
    channel: dict[str, str],
    *,
    listing: list[tuple[str, str]] | None = None,
    fetch_info: Callable[[str], dict] = fetch_video_info,
) -> dict[str, Any]:
    """Fetch the newest non-members-only video metadata for a channel."""
    candidates = listing or get_latest_video_listing(channel)
    last_exc: Exception | None = None
    for url, rss_title in candidates:
        try:
            info = fetch_info(url)
            info["_rss_title"] = rss_title
            return info
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if is_members_only_error(exc):
                print(f"  youtube/{channel['key']}: skip members-only {url}", file=sys.stderr)
                continue
            raise
    raise RuntimeError(
        f"{channel['label']}: no accessible video in listing ({last_exc})"
    )


def build_channel_source(
    channel: dict[str, str],
    info: dict[str, Any],
    topics: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "channel_key": channel["key"],
        "channel_label": channel["label"],
        "channel_id": channel["channel_id"],
        "handle": channel["handle"],
        "video_url": info.get("url", ""),
        "video_title": info.get("title", ""),
        "upload_date": info.get("upload_date", ""),
        "description": info.get("description", ""),
        "topic_count": len(topics),
        "topics": topics,
        "video_resources": order_story_links(
            parse_description_resources(info.get("description") or ""),
            extract_links_from_text(info.get("description") or ""),
        ),
    }


def fetch_channel_source(
    channel: dict[str, str],
    *,
    fetch_info: Callable[[str], dict] = fetch_video_info,
) -> dict[str, Any]:
    info = fetch_accessible_video_info(channel, fetch_info=fetch_info)
    topics, stories = topics_to_story_cards(
        info, channel_key=channel["key"], channel_label=channel["label"]
    )
    source = build_channel_source(channel, info, topics)
    source["_stories"] = stories
    return source


def fetch_youtube_secondary_category(
    *,
    channels: list[dict[str, str]] | None = None,
    max_workers: int = 4,
    fetch_info: Callable[[str], dict] = fetch_video_info,
) -> dict[str, Any]:
    """Aggregate all secondary channels into one ``youtube`` digest category."""
    channels = channels or SECONDARY_CHANNELS
    sources: list[dict[str, Any]] = []
    stories: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    def _one(ch: dict[str, str]) -> tuple[dict[str, str], dict[str, Any] | None, str | None]:
        try:
            src = fetch_channel_source(ch, fetch_info=fetch_info)
            return ch, src, None
        except Exception as exc:  # noqa: BLE001
            return ch, None, str(exc)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_one, ch) for ch in channels]
        for future in as_completed(futures):
            ch, src, err = future.result()
            if err:
                errors.append({"channel_key": ch["key"], "channel_label": ch["label"], "error": err})
                print(f"  youtube/{ch['key']}: FAILED {err[:120]}", file=sys.stderr)
                continue
            batch = src.pop("_stories", [])
            stories.extend(batch)
            sources.append(src)
            print(
                f"  youtube/{ch['key']}: {len(batch)} topics from {src.get('video_title', '')[:50]}",
                file=sys.stderr,
            )

    cat = make_category("youtube", stories)
    cat["sources"] = sources
    if errors:
        cat["_errors"] = errors
    return cat


def format_youtube_ingestion_block(category: dict[str, Any], *, max_chars: int = 16_000) -> str:
    """Render channel descriptions for LLM ingestion context."""
    parts: list[str] = []
    used = 0
    for src in category.get("sources") or []:
        label = src.get("channel_label") or src.get("channel_key") or "YouTube"
        title = src.get("video_title") or ""
        desc = (src.get("description") or "").strip()
        block = f"### {label} — {title}\n{desc}\n"
        if used + len(block) > max_chars:
            block = block[: max_chars - used]
        parts.append(block)
        used += len(block)
        if used >= max_chars:
            break
    return "\n".join(parts).strip()
