"""Extract high-signal outbound links (GitHub, X, LinkedIn, papers, announcements) from text."""

from __future__ import annotations

import html as html_module
import re
from typing import Any
from urllib.parse import urlparse

_URL = re.compile(r"https?://[^\s<>\[\]()\"'\\]+", re.IGNORECASE)
_TOOLS_SECTION = re.compile(
    r"(?:tools?\s*(?:&|and)\s*resources?\s*(?:mentioned)?|resources?\s*mentioned)\s*:?\s*\n",
    re.IGNORECASE,
)
_TIMESTAMP_LINE = re.compile(
    r"^\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\s+(.+?)\s*$",
    re.MULTILINE,
)

_SKIP_HOST_SUBSTR = (
    "youtube.com",
    "youtu.be",
    "ko-fi.com",
    "patreon.com",
    "discord.gg",
    "discord.com/invite",
)

_KIND_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("github", re.compile(r"github\.com", re.I)),
    ("x", re.compile(r"(?:twitter\.com|x\.com)/", re.I)),
    ("linkedin", re.compile(r"linkedin\.com", re.I)),
    ("huggingface", re.compile(r"huggingface\.co", re.I)),
    ("arxiv", re.compile(r"arxiv\.org", re.I)),
]


_A_HREF = re.compile(
    r"""<a[^>]+href=["']([^"'#][^"']*)["'][^>]*>(.*?)</a>""",
    re.IGNORECASE | re.DOTALL,
)

_STORY_TEXT_FIELDS = (
    "title",
    "summary",
    "raw_snippet",
    "source",
    "feed_body",
    "content",
    "description",
    "snippet",
)


def html_embedded_text(html: str) -> str:
    """Turn HTML anchors into ``label: url`` lines plus plain text (for link parsing)."""
    if not html:
        return ""
    if "<" not in html or ">" not in html:
        return html.strip()
    parts: list[str] = []
    for href, inner in _A_HREF.findall(html):
        href = html_module.unescape(href.strip())
        if not href.startswith(("http://", "https://")):
            continue
        label = re.sub(r"<[^>]+>", " ", inner)
        label = html_module.unescape(re.sub(r"\s+", " ", label).strip())
        if label:
            parts.append(f"{label}: {href}")
        else:
            parts.append(href)
    plain = re.sub(r"<[^>]+>", " ", html)
    plain = html_module.unescape(re.sub(r"\s+", " ", plain).strip())
    if plain:
        parts.append(plain)
    return "\n".join(parts)


def story_text_blobs(story: dict[str, Any]) -> list[str]:
    """Collect free-text (and HTML) fields that may embed outbound links."""
    blobs: list[str] = []
    for key in _STORY_TEXT_FIELDS:
        val = story.get(key)
        if not isinstance(val, str) or not val.strip():
            continue
        if "<" in val and ">" in val:
            blobs.append(html_embedded_text(val))
        else:
            blobs.append(val.strip())
    return blobs


def attach_story_embedded_links(story: dict[str, Any]) -> None:
    """Parse GitHub/X/LinkedIn/HF/arXiv/announcement links from all story text fields."""
    existing = story.get("links") or []
    merge_story_links(story, *story_text_blobs(story), primary=existing)


def normalize_url_key(url: str) -> str:
    s = (url or "").strip().lower().rstrip(".,;)")
    if s.startswith("www."):
        s = s[4:]
    return s.split("#", 1)[0].split("?", 1)[0].rstrip("/")


def classify_url(url: str) -> str:
    for kind, pattern in _KIND_RULES:
        if pattern.search(url):
            return kind
    return "web"


def _should_skip_url(url: str, *, allow_bare_domain: bool = False) -> bool:
    low = url.lower()
    if any(host in low for host in _SKIP_HOST_SUBSTR):
        return True
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    if host in {"youtu.be", "www.youtu.be"}:
        return True
    path = (parsed.path or "").strip("/")
    if not path and not parsed.query and not allow_bare_domain:
        return True
    return False


def _name_from_line(line: str, url: str) -> str:
    name = line
    for u in _URL.findall(line):
        name = name.replace(u, "")
    name = re.sub(r"^[-•*:\s]+", "", name)
    name = re.sub(r"[-–—:\s]+$", "", name).strip()
    if name:
        return name[:120]
    kind = classify_url(url)
    if kind == "github":
        path = url.split("github.com/", 1)[-1].split("?")[0].strip("/")
        parts = path.split("/")
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return parts[0] if parts else "GitHub"
    if kind == "x":
        return "Post on X"
    if kind == "linkedin":
        return "LinkedIn"
    if kind == "huggingface":
        return "Hugging Face"
    if kind == "arxiv":
        return "arXiv paper"
    host = urlparse(url).netloc.replace("www.", "")
    return host or "Link"


def _link_record(name: str, url: str) -> dict[str, str]:
    kind = classify_url(url)
    return {"name": name.strip() or kind, "url": url.rstrip(".,;)"), "kind": kind}


def extract_links_from_text(
    text: str,
    *,
    exclude_urls: set[str] | None = None,
    allow_named_product_urls: bool = False,
) -> list[dict[str, str]]:
    """Pull GitHub, X, LinkedIn, HF, arXiv, and announcement URLs from free text."""
    if not text:
        return []
    exclude = {normalize_url_key(u) for u in (exclude_urls or set()) if u}
    links: list[dict[str, str]] = []
    seen: set[str] = set()

    for line in text.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("chapters"):
            continue
        has_named_url = bool(re.match(r"^[-•*:\s]*[^:\n]+:\s*https?://", line, re.I))
        allow_bare = allow_named_product_urls and has_named_url
        for raw in _URL.findall(line):
            url = raw.rstrip(".,;)")
            if _should_skip_url(url, allow_bare_domain=allow_bare):
                continue
            key = normalize_url_key(url)
            if not key or key in seen or key in exclude:
                continue
            kind = classify_url(url)
            if kind == "web":
                path_parts = urlparse(url).path.strip("/").split("/")
                if len(path_parts) < 1 and not (
                    allow_named_product_urls and has_named_url
                ):
                    continue
            seen.add(key)
            links.append(_link_record(_name_from_line(line, url), url))

    priority = {"github": 0, "x": 1, "linkedin": 2, "huggingface": 3, "arxiv": 4, "web": 5}
    links.sort(key=lambda l: (priority.get(l.get("kind") or "web", 9), l["name"].lower()))
    return links


def parse_description_resources(description: str) -> list[dict[str, str]]:
    """Named links from a YouTube ``Tools & resources`` block (or bullet lines)."""
    if not description:
        return []
    section = _TOOLS_SECTION.search(description)
    if section:
        block = description[section.end() :]
        block = re.split(r"\n(?:about |subscribe |#\w)", block, maxsplit=1, flags=re.I)[0]
        return extract_links_from_text(block, allow_named_product_urls=True)
    lines = [
        line
        for line in description.splitlines()
        if _URL.search(line) and (":" in line or line.strip().startswith(("-", "•", "*")))
    ]
    return extract_links_from_text("\n".join(lines), allow_named_product_urls=True)


def _timestamp_to_seconds(hours: str | None, minutes: str, seconds: str) -> int:
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds)


def description_segment(description: str, start_s: int, next_start_s: int | None) -> str:
    if not description:
        return ""
    lines: list[str] = []
    in_segment = False
    for line in description.splitlines():
        m = _TIMESTAMP_LINE.match(line)
        if m:
            hours, minutes, seconds, _title = m.groups()
            ts = _timestamp_to_seconds(hours, minutes, seconds)
            if ts == start_s:
                in_segment = True
                continue
            if in_segment and next_start_s is not None and ts >= next_start_s:
                break
        elif in_segment:
            lines.append(line)
    return "\n".join(lines)


def order_story_links(
    primary: list[dict[str, str]],
    supplemental: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Primary/chapter links first, then remaining deduped links."""
    ordered: list[dict[str, str]] = []
    seen: set[str] = set()
    for link in primary + supplemental:
        url = link.get("url") or ""
        key = normalize_url_key(url)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(
            {
                "name": link.get("name") or url,
                "url": url,
                "kind": link.get("kind") or classify_url(url),
            }
        )
    return ordered


def merge_story_links(
    story: dict[str, Any],
    *texts: str,
    primary: list[dict[str, str]] | None = None,
) -> None:
    """Attach ``links[]`` on a story from text blobs (in-place)."""
    exclude = {story.get("url") or ""}
    combined = "\n".join(t for t in texts if t)
    extracted = extract_links_from_text(combined, exclude_urls=exclude, allow_named_product_urls=True)
    story["links"] = order_story_links(primary or [], extracted)
