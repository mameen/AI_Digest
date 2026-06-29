"""Editorial helpers: category catalog, context assembly, digest ordering."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pipeline.dates import RunWindow
from pipeline.paths import PROJECT_ROOT, SKILL_DIR

BRIEF_PATH = Path(__file__).with_name("editorial_brief.md")

# Canonical digest category order (matches production reports/*.json + extensions)
CATEGORY_CATALOG: dict[str, dict[str, str]] = {
    "leaderboard": {"label": "Leaderboard Rankings", "icon": "🏆"},
    "analytics": {"label": "Analytics & Benchmarks", "icon": "📊"},
    "aisearch": {"label": "AI Search", "icon": "🔍"},
    "agentic-ai": {"label": "Agentic AI", "icon": "🤝"},
    "llm": {"label": "LLMs & Reasoning", "icon": "🧠"},
    "rag": {"label": "RAG & Information Retrieval", "icon": "🗂️"},
    "image-gen": {"label": "Image Generation & Processing", "icon": "🎨"},
    "design-ai": {"label": "Design & Creative AI", "icon": "✏️"},
    "typography": {"label": "Typography & Text Rendering", "icon": "🔤"},
    "robotics": {"label": "Robotics & Embodied AI", "icon": "🤖"},
    "research": {"label": "Research & Papers", "icon": "📄"},
}

CANONICAL_ORDER: list[str] = list(CATEGORY_CATALOG.keys())
SKELETON_CATEGORY_IDS = frozenset({"aisearch", "typography", "research"})
GAP_CATEGORY_IDS = frozenset({
    "analytics",
    "agentic-ai",
    "llm",
    "rag",
    "image-gen",
    "design-ai",
    "robotics",
})
# Preflight uses "category" on some sections; production JSON uses "id"
_PREFLIGHT_META_KEYS = frozenset({"category", "video_url", "video_label"})


def category_id(cat: dict[str, Any]) -> str | None:
    cid = cat.get("id") or cat.get("category")
    return str(cid) if cid else None


def normalize_preflight_category(cat: dict[str, Any]) -> dict[str, Any]:
    """Map preflight category shape → production digest category shape."""
    cid = category_id(cat)
    if not cid:
        return strip_private_fields(cat)
    meta = CATEGORY_CATALOG.get(cid, {"label": cid, "icon": "📌"})
    out = strip_private_fields(cat)
    out["id"] = cid
    out.setdefault("label", meta["label"])
    out.setdefault("icon", meta["icon"])
    return out


def load_editorial_brief() -> str:
    if BRIEF_PATH.is_file():
        return BRIEF_PATH.read_text(encoding="utf-8")
    skill = SKILL_DIR / "SKILL.md"
    if skill.is_file():
        return skill.read_text(encoding="utf-8")[:12_000]
    return "You are the AI Daily Editor. Match production digest style."


def extract_aisearch_meta(categories: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    """Pull video URL/label from preflight aisearch category."""
    for cat in categories:
        if category_id(cat) != "aisearch":
            continue
        url = cat.get("_video_url") or cat.get("video_url") or cat.get("aisearch_video_url")
        title = (
            cat.get("_video_title")
            or cat.get("video_label")
            or cat.get("_video_label")
            or cat.get("aisearch_video_label")
            or ""
        )
        upload = cat.get("_upload_date") or ""
        if not url:
            stories = cat.get("stories") or []
            if stories and stories[0].get("url"):
                url = stories[0]["url"].split("&t=")[0]
        if not url:
            return None, None
        label = title
        if upload and len(upload) == 8:
            try:
                dt = datetime.strptime(upload, "%Y%m%d")
                label = f"{dt.strftime('%b %d')}: {title}" if title else dt.strftime("%b %d")
            except ValueError:
                pass
        return url, label
    return None, None


def strip_private_fields(cat: dict[str, Any]) -> dict[str, Any]:
    return {
        k: v
        for k, v in cat.items()
        if not str(k).startswith("_") and k not in _PREFLIGHT_META_KEYS
    }


def normalize_category_metadata(cat: dict[str, Any]) -> dict[str, Any]:
    """Force canonical label/icon from CATEGORY_CATALOG (LLM gap-fill often drifts)."""
    cid = cat.get("id")
    if not cid:
        return cat
    meta = CATEGORY_CATALOG.get(cid, {"label": cat.get("label", cid), "icon": cat.get("icon", "📌")})
    return {**cat, "id": cid, "label": meta["label"], "icon": meta["icon"]}


def order_categories(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {c["id"]: normalize_category_metadata(c) for c in categories if c.get("id")}
    ordered: list[dict[str, Any]] = []
    for cid in CANONICAL_ORDER:
        if cid in by_id:
            ordered.append(by_id[cid])
    for cid, cat in by_id.items():
        if cid not in CANONICAL_ORDER:
            ordered.append(cat)
    return ordered


def make_category(cat_id: str, stories: list[dict[str, Any]]) -> dict[str, Any]:
    meta = CATEGORY_CATALOG.get(cat_id, {"label": cat_id, "icon": "📌"})
    return {
        "id": cat_id,
        "label": meta["label"],
        "icon": meta["icon"],
        "stories": stories,
    }


def build_ingestion_context(
    skeleton: dict[str, Any],
    crawl_md: list[Path],
    *,
    max_crawl_chars: int = 32_000,
    max_llm_stats_chars: int = 16_000,
) -> str:
    parts: list[str] = []

    llm_stats = skeleton.get("llm_stats") or {}
    if llm_stats.get("text"):
        parts.append("## LLM Stats (llm-stats.com)\n" + str(llm_stats["text"])[:max_llm_stats_chars])
    elif llm_stats.get("error"):
        parts.append(f"## LLM Stats error\n{llm_stats['error']}")

    for item in skeleton.get("requires_web_fetch") or []:
        parts.append(
            f"- {item.get('label')}: {item.get('url')} ({item.get('why', '')})"
        )

    crawl_used = 0
    for path in crawl_md:
        text = path.read_text(encoding="utf-8")
        chunk = f"\n\n## Crawl: {path.name}\n{text}"
        if crawl_used + len(chunk) > max_crawl_chars:
            chunk = chunk[: max_crawl_chars - crawl_used]
        parts.append(chunk)
        crawl_used += len(chunk)
        if crawl_used >= max_crawl_chars:
            break

    return "\n".join(parts)


def skeleton_category_map(skeleton: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in skeleton.get("categories") or []:
        cat = normalize_preflight_category(raw)
        cid = cat.get("id")
        if cid:
            out[cid] = cat
    return out


def stories_for_prompt(stories: list[dict[str, Any]], limit: int | None = None) -> str:
    batch = stories if limit is None else stories[:limit]
    return json.dumps(batch, indent=2, ensure_ascii=False)


def enrich_cfg(cfg: dict[str, Any]) -> dict[str, Any]:
    return cfg.get("enrich") or {}


# Production-style defaults (Jun 27 2026 reference digest)
DEFAULT_CATEGORY_TARGETS: dict[str, int | None] = {
    "leaderboard": 6,
    "analytics": 5,
    "aisearch": 10,
    "agentic-ai": 5,
    "llm": 5,
    "rag": 5,
    "image-gen": 5,
    "design-ai": 5,
    "typography": 4,
    "robotics": 5,
    "research": 6,
}


def category_targets(cfg: dict[str, Any]) -> dict[str, int | None]:
    raw = enrich_cfg(cfg).get("category_targets") or {}
    out = dict(DEFAULT_CATEGORY_TARGETS)
    for key, val in raw.items():
        out[key] = None if val is None else int(val)
    return out


def target_for(cfg: dict[str, Any], cat_id: str) -> int | None:
    return category_targets(cfg).get(cat_id)
