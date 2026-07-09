"""URL verify + keyless web search for agentic Hermes workers.

Fork of ``llm_pipeline/tools.py`` (``verify_url``, ``web_search`` and helpers).
Keep in sync manually until pipeline deprecation (ADR 002). The staged pipeline
uses a prompt-registered JSON loop; Hermes exposes ``verify_url`` via the
``digest-tools`` plugin and ``web_search`` via Hermes ``web.backend ddgs``.
"""

from __future__ import annotations

import html as _html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

_UA = {"User-Agent": "AI-Digest/1.0 (+link-verify)"}
FetchStatus = Callable[[str, int], "tuple[int | None, str, str]"]
FetchHtml = Callable[[str, int], str]

_MAX_BODY_BYTES = 131072
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_NOT_FOUND_TITLE_MARKERS = ("not found", "page not found", "404 not found", "error 404")
_NOT_FOUND_BODY_MARKERS = (
    "page not found",
    "page could not be found",
    "page doesn't exist",
    "page you requested could not",
    "looks like you're lost",
)
_TAG_RE = re.compile(r"<[^>]+>")


def _http_fetch(url: str, timeout: int) -> tuple[int | None, str, str]:
    req = urllib.request.Request(url, headers=_UA, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = int(getattr(resp, "status", 0) or resp.getcode())
            body = resp.read(_MAX_BODY_BYTES).decode("utf-8", errors="replace")
            return status, resp.geturl(), body
    except urllib.error.HTTPError as exc:
        return int(exc.code), url, ""
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None, url, ""


def looks_not_found(body: str) -> bool:
    if not body:
        return False
    match = _TITLE_RE.search(body)
    if match:
        title = _html.unescape(_TAG_RE.sub("", match.group(1))).strip().lower()
        if any(mark in title for mark in _NOT_FOUND_TITLE_MARKERS):
            return True
    head = body[:8000].lower()
    return any(mark in head for mark in _NOT_FOUND_BODY_MARKERS)


def verify_url(url: str, *, fetch: FetchStatus | None = None, timeout: int = 8) -> dict[str, Any]:
    u = (url or "").strip()
    if not u.lower().startswith(("http://", "https://")):
        return {"url": url, "ok": False, "status": None, "error": "not-an-http-url"}
    status, final_url, body = (fetch or _http_fetch)(u, timeout)
    live = status is not None and 200 <= status < 400
    soft_404 = live and looks_not_found(body)
    ok = live and not soft_404
    out: dict[str, Any] = {"url": u, "ok": ok, "status": status, "final_url": final_url}
    if not ok:
        if status is None:
            out["error"] = "unreachable"
        elif soft_404:
            out["error"] = "soft-404: page content is 'not found'"
    return out


_DDG_ENDPOINT = "https://html.duckduckgo.com/html/"
_RESULT_A_RE = re.compile(
    r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def _ddg_target(href: str) -> str | None:
    href = _html.unescape(href or "")
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [None])[0]
        return target
    return href if href.startswith(("http://", "https://")) else None


def parse_ddg_results(html_text: str, *, limit: int = 5) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for href, inner in _RESULT_A_RE.findall(html_text or ""):
        url = _ddg_target(href)
        if not url or url in seen:
            continue
        title = _html.unescape(_TAG_RE.sub("", inner)).strip()
        if not title:
            continue
        seen.add(url)
        results.append({"title": title, "url": url})
        if len(results) >= limit:
            break
    return results


def _fetch_ddg_html(query: str, timeout: int) -> str:
    data = urllib.parse.urlencode({"q": query}).encode()
    req = urllib.request.Request(_DDG_ENDPOINT, data=data, headers=_UA, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def web_search(
    query: str, *, fetch_html: FetchHtml | None = None, limit: int = 5, timeout: int = 8
) -> dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"query": query, "results": [], "error": "empty-query"}
    try:
        html_text = (fetch_html or _fetch_ddg_html)(q, timeout)
    except Exception as exc:
        return {"query": q, "results": [], "error": str(exc)}
    return {"query": q, "results": parse_ddg_results(html_text, limit=limit)}


def verify_url_json(args: dict[str, Any]) -> str:
    """Hermes plugin handler — returns JSON string."""
    try:
        timeout = int(args.get("timeout", 8))
    except (TypeError, ValueError):
        timeout = 8
    return json.dumps(verify_url(str(args.get("url") or ""), timeout=timeout), default=str)
