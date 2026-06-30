"""Structured-API leaderboard sources.

A second source *kind* alongside the Crawl4AI markdown crawl: endpoints that
already publish structured JSON, so they need fetching but no scraping. Each
source maps onto a tab in the ``leaderboards`` object (see ``template.html``)
and is injected at render time with the same brace/bracket-aware helpers that
drive the crawl tables, so the tabs are API-driven and never stale.

Verified live endpoints (probed 2026-06-30):
  * SWE-bench — the canonical ``data/leaderboards.json`` the official site builds
    from; the AA/Vellum-style scrapes have no public API.
  * EvalPlus — ``results.json`` keyed by model name (HumanEval+/MBPP+ pass@1).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from pipeline.leaderboards import render_rows_js, replace_field_array, set_field_string

STRUCTURED_SOURCES: list[dict[str, str]] = [
    {
        "key": "swe",
        "slug": "swebench_leaderboards.json",
        "url": "https://raw.githubusercontent.com/SWE-bench/swe-bench.github.io/master/data/leaderboards.json",
        "label": "SWE-bench Verified",
        "source": "swebench.com",
        "parser": "swebench",
    },
    {
        "key": "coding",
        "slug": "evalplus_results.json",
        "url": "https://evalplus.github.io/results.json",
        "label": "EvalPlus (HumanEval+)",
        "source": "evalplus.github.io",
        "parser": "evalplus",
    },
]


def _val(x: Any) -> Any:
    """None / missing → em-dash placeholder the widget already understands."""
    return "—" if x is None else x


def _size_cell(size: Any) -> Any:
    if size is None:
        return "—"
    try:
        f = float(size)
    except (TypeError, ValueError):
        return size
    return int(f) if f.is_integer() else f


# ── JSON → rows in each tab's column order ───────────────────────────────────
def evalplus_rows(data: dict[str, Any], limit: int = 15) -> list[list[Any]]:
    """``{model: {pass@1: {...}, size}}`` → rows ranked by HumanEval+ desc."""
    ranked = sorted(
        data.items(),
        key=lambda kv: ((kv[1].get("pass@1") or {}).get("humaneval+") or -1),
        reverse=True,
    )
    rows: list[list[Any]] = []
    for i, (name, v) in enumerate(ranked[:limit], start=1):
        p = v.get("pass@1") or {}
        rows.append([i, name, _size_cell(v.get("size")), _val(p.get("humaneval+")), _val(p.get("mbpp+"))])
    return rows


def swebench_rows(data: dict[str, Any], board: str = "Verified", limit: int = 15) -> list[list[Any]]:
    """``{leaderboards: [{name, results: [...]}]}`` → rows ranked by resolved desc."""
    boards = data.get("leaderboards") or []
    target = next((b for b in boards if str(b.get("name", "")).lower() == board.lower()), None)
    if not target:
        return []
    results = sorted(target.get("results") or [], key=lambda r: (r.get("resolved") or -1), reverse=True)
    rows: list[list[Any]] = []
    for i, r in enumerate(results[:limit], start=1):
        rows.append([i, r.get("name") or "", _val(r.get("resolved")), r.get("date") or "—"])
    return rows


_PARSERS: dict[str, Callable[..., list[list[Any]]]] = {
    "evalplus": evalplus_rows,
    "swebench": swebench_rows,
}


def apply_structured_leaderboards(
    block: str, structured_dir: Path, updated_label: str | None = None, limit: int = 15
) -> str:
    """Overwrite each structured tab's rows from its cached JSON, when present."""
    structured_dir = Path(structured_dir)
    for src in STRUCTURED_SOURCES:
        path = structured_dir / src["slug"]
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        rows = _PARSERS[src["parser"]](data, limit=limit)
        if not rows:
            continue
        block = replace_field_array(block, src["key"], "rows", render_rows_js(rows))
        if updated_label:
            block = set_field_string(block, src["key"], "updated", updated_label)
    return block
