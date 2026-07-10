"""Empty digest scaffold — canonical categories without baseline carry-forward."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from llm_pipeline.editorial import CANONICAL_ORDER, CATEGORY_CATALOG


def empty_digest(prefix: str, *, summary: str = "") -> dict[str, Any]:
    """Build a 12-category digest shell for a run prefix (no pinned baseline)."""
    categories: list[dict[str, Any]] = []
    for cid in CANONICAL_ORDER:
        meta = CATEGORY_CATALOG[cid]
        categories.append(
            {
                "id": cid,
                "label": meta["label"],
                "icon": meta["icon"],
                "stories": [],
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filename_prefix": prefix,
        "summary": summary,
        "categories": categories,
    }
