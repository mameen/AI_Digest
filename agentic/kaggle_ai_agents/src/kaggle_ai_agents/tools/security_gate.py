"""Security gate: deny-list filter applied to fetched items before they enter the pipeline.

filter_items(items) -> FilterResult
  .passed  — clean items safe to continue
  .blocked — items that triggered a rule, each with a .reason string
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from kaggle_ai_agents.models import NewsItem

# ── Deny-list patterns ────────────────────────────────────────────────────────

_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(all\s+)?previous\s+instructions\b", re.I),
    re.compile(r"\bnew\s+instructions\b.*\byou\s+are\s+now\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(previous\s+)?(rules|instructions|guidelines)\b", re.I),
    re.compile(r"\breveal\s+(your\s+)?(system\s+prompt|instructions|context)\b", re.I),
    re.compile(r"\bforget\s+(everything|all\s+(previous|prior|above))\b", re.I),
]

_HTML_INJECTION_PATTERN = re.compile(r"<\s*(script|iframe|object|embed|form)\b", re.I)

_DANGEROUS_URL_SCHEMES = {"javascript", "data", "vbscript", "file"}


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class BlockedItem:
    item: NewsItem
    reason: str


@dataclass
class FilterResult:
    passed: list[NewsItem] = field(default_factory=list)
    blocked: list[BlockedItem] = field(default_factory=list)


class SecurityViolation(Exception):
    """Raised when a hard security violation is detected (not just a filtered item)."""


# ── Core filter ───────────────────────────────────────────────────────────────

def _check_url(url: str) -> str | None:
    """Return a violation reason if the URL is dangerous, else None."""
    try:
        scheme = urlparse(url).scheme.lower()
    except Exception:
        return "unparseable URL"
    if scheme in _DANGEROUS_URL_SCHEMES:
        return f"dangerous URL scheme: {scheme!r}"
    return None


def _check_text(text: str) -> str | None:
    """Return a violation reason if the text contains an injection pattern, else None."""
    if _HTML_INJECTION_PATTERN.search(text):
        return "HTML injection in text"
    for pat in _PROMPT_INJECTION_PATTERNS:
        if pat.search(text):
            return f"prompt injection pattern: {pat.pattern!r}"
    return None


def filter_items(items: list[NewsItem]) -> FilterResult:
    """Apply security deny-list to a list of items. Returns passed and blocked items."""
    result = FilterResult()
    for item in items:
        reason = (
            _check_url(str(item.url))
            or _check_text(item.title)
            or _check_text(item.summary)
        )
        if reason:
            result.blocked.append(BlockedItem(item=item, reason=reason))
        else:
            result.passed.append(item)
    return result
