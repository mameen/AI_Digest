"""Load prior digest JSON for editorial / LLM context within the lookback window."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from llm_pipeline.dates import RunWindow
from llm_pipeline.paths import reports_dir


def _prefix_date(prefix: str) -> date | None:
    if len(prefix) != 14 or not prefix.isdigit():
        return None
    try:
        return date(int(prefix[0:4]), int(prefix[4:6]), int(prefix[6:8]))
    except ValueError:
        return None


def _digest_json_paths(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        p
        for p in root.glob("*.json")
        if p.name != "index.json" and len(p.stem) == 14 and p.stem.isdigit()
    )


def load_prior_digests(cfg: dict[str, Any], window: RunWindow) -> list[dict[str, Any]]:
    """Digests after ``history_from`` and strictly before ``window.start``."""
    root = reports_dir(cfg)
    prior: list[tuple[str, dict[str, Any]]] = []

    for path in _digest_json_paths(root):
        pfx_date = _prefix_date(path.stem)
        if pfx_date is None or pfx_date >= window.start or pfx_date < window.history_from:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        prior.append((path.stem, data))

    prior.sort(key=lambda x: x[0])
    return [data for _, data in prior]


def format_prior_context(digests: list[dict[str, Any]], max_chars: int = 24_000) -> str:
    if not digests:
        return "(no prior digests in window)"

    parts: list[str] = []
    used = 0
    for data in digests:
        pfx = data.get("filename_prefix", "?")
        summary = data.get("summary") or ""
        cats = len(data.get("categories") or [])
        stories = sum(len(c.get("stories") or []) for c in data.get("categories") or [])
        block = f"### {pfx}\n{summary}\n({cats} categories, {stories} stories)\n"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts)
