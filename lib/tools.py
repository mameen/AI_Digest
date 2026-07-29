"""Prompt-registered tool-calling loop for grounding gap-filled stories.

The gap-fill model can cite a plausible URL it never actually saw. Instead of
only demoting such links after the fact (the deterministic guard in
:mod:`llm_pipeline.grounding`), this module lets the model *actively* check and
repair them: it is told, in the prompt, that it may emit a single JSON tool
action per turn, we execute the tool, and feed the observation back until it
``finalize``s or the iteration budget runs out.

The client is wired as ``instructor.Mode.JSON`` (one Pydantic reply per call),
so the loop runs as free-form JSON **outside** Instructor; the caller does one
final Instructor pass to coerce the finalized text into ``GapCategories``. All
network I/O is behind injectable callables so the pure logic is testable
offline with committed fixtures (see ``tests/test_tools.py``).
"""

from __future__ import annotations

import html as _html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

_UA = {"User-Agent": "AI-Digest/1.0 (+link-verify)"}
FetchStatus = Callable[[str, int], "tuple[int | None, str, str]"]
FetchHtml = Callable[[str, int], str]
Chat = Callable[[list[dict[str, str]]], str]
Tool = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class ToolAction:
    """One parsed tool request from the model."""

    name: str
    args: dict[str, Any]
    raw: str


def parse_tool_action(text: str) -> ToolAction | None:
    """Extract the first JSON object with an ``action`` key from model text.

    Tolerant of code fences and surrounding prose: scans for the first
    brace-balanced ``{...}`` and parses it. Returns ``None`` when no valid
    action object is present (the driver then asks for a reformat).
    """
    obj = _first_json_object(text or "")
    if not isinstance(obj, dict):
        return None
    name = obj.get("action")
    if not isinstance(name, str) or not name:
        return None
    args = obj.get("args")
    return ToolAction(name=name.strip(), args=args if isinstance(args, dict) else {}, raw=text)


def _first_json_object(text: str) -> Any:
    depth = 0
    start = -1
    in_str = False
    esc = False
    quote = ""
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
            continue
        if ch in "\"'":
            in_str, quote = True, ch
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    start = -1
    return None


def format_tool_result(action: ToolAction, result: Any) -> str:
    """Compact observation message fed back to the model next turn."""
    payload = json.dumps(result, ensure_ascii=False, default=str)
    return f"OBSERVATION {action.name}: {payload}"


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


def _http_fetch(url: str, timeout: int) -> tuple[int | None, str, str]:
    """GET the URL, returning ``(status, final_url, body)`` with the body capped.

    A GET (rather than HEAD) is required so the caller can inspect content for a
    soft 404 — an SPA that answers ``200`` with a client-rendered "not found"
    screen. The body read is bounded to keep verification cheap.
    """
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
    """Heuristically flag a soft 404: a page whose *content* says "not found".

    Conservative to avoid false positives — trusts the ``<title>`` first, then a
    short set of unambiguous phrases in the page's head region. A genuine
    article (descriptive title, no such phrases) is never flagged.
    """
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
    """Content-aware liveness check for a single URL.

    ``ok`` requires *both* a 2xx/3xx response **and** that the returned page is
    not a soft 404 (a ``200`` whose content is a "not found" screen — common for
    SPAs like figure.ai). ``fetch`` is injectable
    ``(url, timeout) -> (status, final_url, body)`` so tests exercise the shaping
    logic against real fixture pages without touching the network.
    """
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
_TAG_RE = re.compile(r"<[^>]+>")


def _ddg_target(href: str) -> str | None:
    """Resolve a DuckDuckGo result href to its real target URL.

    HTML-endpoint links are redirect shims ``//duckduckgo.com/l/?uddg=<enc>``;
    the actual destination lives in the ``uddg`` query param.
    """
    href = _html.unescape(href or "")
    if href.startswith("//"):
        href = "https:" + href
    parsed = urllib.parse.urlparse(href)
    if "duckduckgo.com" in parsed.netloc and parsed.path.startswith("/l/"):
        target = urllib.parse.parse_qs(parsed.query).get("uddg", [None])[0]
        return target
    return href if href.startswith(("http://", "https://")) else None


def parse_ddg_results(html_text: str, *, limit: int = 5) -> list[dict[str, str]]:
    """Extract ``[{title, url}]`` rows from a DuckDuckGo HTML results page.

    Deduplicates by target URL and caps at ``limit``. Pure function over the
    committed fixture (``tests/data/duckduckgo_html_results.html``).
    """
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
    """POST the query to DuckDuckGo's HTML endpoint (its GET form returns no rows)."""
    data = urllib.parse.urlencode({"q": query}).encode()
    req = urllib.request.Request(_DDG_ENDPOINT, data=data, headers=_UA, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def web_search(
    query: str, *, fetch_html: FetchHtml | None = None, limit: int = 5, timeout: int = 8
) -> dict[str, Any]:
    """Keyless web search via DuckDuckGo's HTML endpoint.

    ``fetch_html`` is injectable ``(query, timeout) -> html`` so tests parse the
    committed fixture without touching the network. Returns
    ``{"query", "results": [{title, url}], ...}``.
    """
    q = (query or "").strip()
    if not q:
        return {"query": query, "results": [], "error": "empty-query"}
    try:
        html_text = (fetch_html or _fetch_ddg_html)(q, timeout)
    except Exception as exc:  # network failures surface as an observation, not a crash
        return {"query": q, "results": [], "error": str(exc)}
    return {"query": q, "results": parse_ddg_results(html_text, limit=limit)}


TOOL_CATALOG: dict[str, Tool] = {"verify_url": verify_url}

_REFORMAT_HINT = (
    "Reply with exactly ONE JSON object and nothing else: "
    '{"action": "<tool>", "args": {...}} or {"action": "finalize", "args": {"result": "<json>"}}.'
)


def run_tool_loop(
    chat: Chat,
    system: str,
    user: str,
    tools: dict[str, Tool],
    *,
    max_iterations: int = 12,
    nudge_before_finalize: bool = False,
) -> tuple[str | None, list[dict[str, Any]]]:
    """Bounded prompt-registered tool loop.

    Returns ``(finalized_text_or_None, call_log)`` where ``call_log`` entries
    have keys ``tool``, ``args``, ``result``, ``duration_ms``.
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    call_log: list[dict[str, Any]] = []

    for _ in range(max_iterations):
        # ── emit tool actions ───────────────────────────────────────────────
        reply = chat(messages)
        action = parse_tool_action(reply)
        if not action:
            return None, call_log  # no valid action → bail

        # ── execute tool ────────────────────────────────────────────────────
        t0 = time.monotonic()
        tool_fn = tools.get(action.name)
        if tool_fn is None:
            result = {"error": f"unknown tool: {action.name}"}
        else:
            try:
                result = tool_fn(**(action.args or {}))
            except Exception as exc:
                result = {"error": str(exc)}
        duration_ms = (time.monotonic() - t0) * 1000

        call_log.append({
            "tool": action.name,
            "args": action.args,
            "result": result,
            "duration_ms": round(duration_ms, 1),
        })

        # ── feed observation back ───────────────────────────────────────────
        messages.append({"role": "assistant", "content": reply})
        messages.append({"role": "tool", "content": format_tool_result(action, result)})

        # ── check for finalize ──────────────────────────────────────────────
        if action.name == "finalize":
            return action.args.get("result"), call_log

    # budget exhausted — ask for a reformat
    if nudge_before_finalize:
        messages.append({"role": "user", "content": _REFORMAT_HINT})
        reply = chat(messages)
        action = parse_tool_action(reply)
        if action and action.name == "finalize":
            return action.args.get("result"), call_log

    return None, call_log
