"""Showcase-shaped digest assembly — researcher overlay on empty 12-category scaffold."""

from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_pipeline.editorial import CANONICAL_ORDER, CATEGORY_CATALOG, category_id
from lib.paths import LLM_PIPELINE_ROOT
from llm_pipeline.paths import reports_dir

from tools.artifacts import _parse_bullet_stories, _read_research_output, _research_topic
from tools.category_merge import merge_stories_by_url
from tools.digest_scaffold import empty_digest

from tools.topics import research_category_ids

_BASELINE_PREFIX = "20260703120000"
_BASELINE_CANDIDATES = (
    "20260703120000.json",
    "20260704120000.json",
    "20260705120000.json",
)


def _digest_json_paths(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(
        p
        for p in root.glob("*.json")
        if p.name != "index.json" and len(p.stem) == 14 and p.stem.isdigit()
    )


def load_baseline_digest(cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load pinned showcase baseline JSON (optional fallback for batch/A/B tooling)."""
    root = reports_dir(cfg or {"output": {"reports_dir": "reports"}})
    pinned = root / f"{_BASELINE_PREFIX}.json"
    if pinned.is_file():
        return copy.deepcopy(json.loads(pinned.read_text(encoding="utf-8")))

    for name in _BASELINE_CANDIDATES:
        path = LLM_PIPELINE_ROOT / "reports" / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))

    best: tuple[int, int, dict[str, Any]] | None = None
    for path in _digest_json_paths(root):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cats = data.get("categories") or []
        stories = sum(len(c.get("stories") or []) for c in cats if isinstance(c, dict))
        score = (len(cats), stories)
        if best is None or score > (best[0], best[1]):
            best = (len(cats), stories, data)

    if best:
        return copy.deepcopy(best[2])

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filename_prefix": "00000000000000",
        "summary": "Baseline digest unavailable.",
        "categories": [],
    }


def _research_stories_by_category(
    research_rows: list[dict[str, Any]],
    *,
    prefix: str | None = None,
    hermes_home: Path | None = None,
) -> dict[str, list[dict[str, Any]]]:
    home = hermes_home or Path.home() / ".hermes"
    allowed = research_category_ids()
    out: dict[str, list[dict[str, Any]]] = {}
    for row in research_rows:
        topic = _research_topic(str(row.get("title", "")))
        if topic not in allowed:
            continue
        text = _read_research_output(row, prefix=prefix, hermes_home=home)
        if not text:
            continue
        stories = _parse_bullet_stories(text, topic)
        if stories:
            out[topic] = stories
    return out


def assemble_showcase_digest(
    research_rows: list[dict[str, Any]],
    *,
    prefix: str | None = None,
    cfg: dict[str, Any] | None = None,
    hermes_home: Path | None = None,
) -> dict[str, Any]:
    """Merge researcher artifacts into a showcase-shaped digest (12 categories)."""
    run_prefix = prefix or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    digest = empty_digest(run_prefix)

    overlay = _research_stories_by_category(
        research_rows, prefix=run_prefix, hermes_home=hermes_home
    )
    cat_by_id: dict[str, dict[str, Any]] = {}
    for cat in digest.get("categories") or []:
        cid = category_id(cat)
        if cid:
            cat_by_id[cid] = cat

    for cid in CANONICAL_ORDER:
        meta = CATEGORY_CATALOG.get(cid, {"label": cid, "icon": "📌"})
        if cid in overlay:
            existing = (cat_by_id.get(cid) or {}).get("stories") or []
            merged = merge_stories_by_url(existing, overlay[cid])
            cat_by_id[cid] = {
                "id": cid,
                "label": meta["label"],
                "icon": meta["icon"],
                "stories": merged,
            }
        elif cid not in cat_by_id:
            cat_by_id[cid] = {
                "id": cid,
                "label": meta["label"],
                "icon": meta["icon"],
                "stories": [],
            }

    categories: list[dict[str, Any]] = []
    for cid in CANONICAL_ORDER:
        cat = cat_by_id.get(cid)
        if not cat:
            continue
        stories = cat.get("stories") or []
        stamped: list[dict[str, Any]] = []
        for story in stories:
            s = copy.deepcopy(story)
            prov = s.get("provenance") or ""
            if cid in overlay and prov.startswith("agent:researcher:"):
                s["provenance"] = prov
            elif cid in overlay:
                s["provenance"] = f"agent:researcher:{cid}"
            stamped.append(s)
        categories.append(
            {
                "id": cid,
                "label": cat.get("label") or meta["label"],
                "icon": cat.get("icon") or meta["icon"],
                "stories": stamped,
            }
        )

    digest["categories"] = categories
    researched = ", ".join(sorted(overlay.keys())) or "(none)"
    digest["summary"] = (
        f"Agentic digest: fresh research on {researched}; "
        "other categories empty (use pipeline GO for full ingest)."
    )
    return digest
