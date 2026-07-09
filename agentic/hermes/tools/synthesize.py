"""LLM synthesizer — compose digest.json from librarian.md (Instructor)."""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_pipeline.editorial import CANONICAL_ORDER, CATEGORY_CATALOG, category_id, load_editorial_brief
from llm_pipeline.llm_client import make_client
from llm_pipeline.schema import CategoryStories, DigestHeader

from tools.artifacts import DIGEST_ARTIFACT, LIBRARIAN_ARTIFACT, validate_synthesizer_artifact
from tools.category_merge import merge_stories_by_url
from tools.showcase import load_baseline_digest

_SECTION_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)
_URL_RE = re.compile(r"https?://[^\s\)>\"]+")

_CATEGORY_HINTS: list[tuple[str, tuple[str, ...]]] = [
    ("leaderboard", ("leaderboard", "ranking")),
    ("analytics", ("pricing", "cost", "analytics", "benchmark")),
    ("agentic-ai", ("agentic", "tool use", "tool-use")),
    ("llm", ("industry", "llm", "work", "organizational")),
    ("aisearch", ("search", "aisearch")),
    ("research", ("evaluation framework", "evalplus", "swe-bench", "eval ", "framework", "paper")),
    ("rag", ("rag", "retrieval")),
    ("robotics", ("robot", "embodied")),
    ("youtube", ("youtube", "video")),
    ("image-gen", ("image gen", "image-gen", "diffusion")),
    ("design-ai", ("design", "creative")),
    ("typography", ("typography", "font", "text render")),
]


def infer_category_id(section_title: str) -> str:
    lower = section_title.lower()
    for cid, hints in _CATEGORY_HINTS:
        if any(h in lower for h in hints):
            return cid
    return "research"


def parse_librarian_entries(text: str) -> list[dict[str, Any]]:
    """Extract story candidates from librarian merged-entry sections."""
    entries: list[dict[str, Any]] = []
    parts = _SECTION_RE.split(text)
    # split returns [preamble, title1, body1, title2, body2, ...]
    idx = 1
    while idx + 1 < len(parts):
        title = parts[idx].strip()
        body = parts[idx + 1]
        idx += 2
        if "merged entries" in title.lower() or title.lower().startswith("topic map"):
            continue
        urls = _URL_RE.findall(body)
        url = urls[0].rstrip(".,)") if urls else None
        claim = ""
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("- **claim:**"):
                claim = stripped.split(":", 1)[-1].strip()
                break
        why = ""
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("- **why it matters:**"):
                why = stripped.split(":", 1)[-1].strip()
                break
        summary = " ".join(p for p in (claim, why) if p).strip() or title
        if not url:
            continue
        entries.append(
            {
                "section": title,
                "category_id": infer_category_id(title),
                "title": claim[:120] if claim else title[:120],
                "summary": summary,
                "url": url,
                "source": "Librarian",
            }
        )
    return entries


def _llm_call(client: Any, model: str, max_retries: int, prompt: str, response_model: type) -> Any:
    from llm_pipeline.diagnostics import instrumented_llm_call

    return instrumented_llm_call(
        client, model, max_retries, prompt, response_model, call_name="agentic.synthesize"
    )


def _group_entries(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        cid = str(entry.get("category_id") or "research")
        grouped.setdefault(cid, []).append(entry)
    return grouped


def synthesize_digest_from_librarian(
    workspace: Path,
    *,
    prefix: str,
    cfg: dict[str, Any],
    librarian_text: str | None = None,
) -> dict[str, Any]:
    """LLM editorial pass: librarian merge → digest.json in workspace."""
    workspace.mkdir(parents=True, exist_ok=True)
    lib_path = workspace / LIBRARIAN_ARTIFACT
    if librarian_text is None:
        if not lib_path.is_file():
            return {"ok": False, "error": f"missing {lib_path}"}
        librarian_text = lib_path.read_text(encoding="utf-8")

    entries = parse_librarian_entries(librarian_text)
    if not entries:
        return {"ok": False, "error": "librarian.md has no URL-bearing merged entries"}

    if not (cfg.get("llm") or {}).get("enabled", True):
        return {"ok": False, "error": "llm disabled in config"}

    try:
        client, model, max_retries = make_client(cfg)
    except SystemExit as exc:
        return {"ok": False, "error": f"LLM client unavailable: {exc}"}

    brief = load_editorial_brief()
    grouped = _group_entries(entries)
    baseline = load_baseline_digest(cfg)
    baseline_prefix = str(baseline.get("filename_prefix") or "baseline")
    digest = copy.deepcopy(baseline)
    digest["filename_prefix"] = prefix
    digest["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    cat_by_id: dict[str, dict[str, Any]] = {}
    for cat in digest.get("categories") or []:
        cid = category_id(cat)
        if cid:
            cat_by_id[cid] = cat

    warnings: list[str] = []
    story_idx = 0
    for cid, raw_stories in grouped.items():
        meta = CATEGORY_CATALOG.get(cid, {"label": cid, "icon": "📌"})
        prompt = f"""{brief}

## Task
You are the AI Digest Synthesizer. Turn these librarian merge entries into polished
stories for category **{meta['label']}** (`{cid}`).
Preserve every `url` exactly. Write magazine-quality titles and 2-3 sentence summaries.
Assign significance, novelty, relevance_design (1-5). Add concise tags.

## Librarian entries
{json.dumps(raw_stories, indent=2)[:14000]}

Return JSON with stories array only."""
        try:
            enriched = _llm_call(client, model, max_retries, prompt, CategoryStories)
            stamped: list[dict[str, Any]] = []
            for s in enriched.stories:
                d = s.model_dump()
                story_idx += 1
                d["id"] = d.get("id") or f"agent-syn-{cid}-{story_idx}"
                d["provenance"] = f"agent:synthesizer:{cid}"
                stamped.append(d)
            cat_by_id[cid] = {
                "id": cid,
                "label": meta["label"],
                "icon": meta["icon"],
                "stories": merge_stories_by_url(
                    (cat_by_id.get(cid) or {}).get("stories") or [],
                    stamped,
                ),
            }
        except Exception as exc:
            warnings.append(f"category {cid} LLM failed: {exc}")
            return {
                "ok": False,
                "error": f"synthesizer LLM failed for category {cid}: {exc}",
                "warnings": warnings,
            }

    categories: list[dict[str, Any]] = []
    for cid in CANONICAL_ORDER:
        meta = CATEGORY_CATALOG.get(cid, {"label": cid, "icon": "📌"})
        cat = cat_by_id.get(cid)
        if not cat:
            cat = {"id": cid, "label": meta["label"], "icon": meta["icon"], "stories": []}
        stories = cat.get("stories") or []
        stamped_stories: list[dict[str, Any]] = []
        for story in stories:
            s = copy.deepcopy(story)
            prov = str(s.get("provenance") or "")
            if cid in grouped:
                s["provenance"] = prov or f"agent:synthesizer:{cid}"
            else:
                s["provenance"] = prov or f"carry:agentic:{baseline_prefix}"
            stamped_stories.append(s)
        categories.append(
            {
                "id": cid,
                "label": cat.get("label") or meta["label"],
                "icon": cat.get("icon") or meta["icon"],
                "stories": stamped_stories,
            }
        )

    digest["categories"] = categories
    title_sample = "; ".join(
        str(s.get("title") or "")
        for c in categories
        for s in (c.get("stories") or [])[:2]
        if s.get("title")
    )[:500]
    summary_prompt = f"""{brief}

## Task
Write one executive takeaway for today's AI digest from the librarian merge.
Today's synthesized stories include: {title_sample}

Return JSON with summary field only."""
    try:
        header = _llm_call(client, model, max_retries, summary_prompt, DigestHeader)
        digest["summary"] = header.summary
    except Exception as exc:
        return {
            "ok": False,
            "error": f"synthesizer summary LLM failed: {exc}",
            "warnings": warnings,
        }

    digest_path = workspace / DIGEST_ARTIFACT
    digest_path.write_text(json.dumps(digest, indent=2) + "\n", encoding="utf-8")
    ok = not validate_synthesizer_artifact(workspace)
    return {
        "ok": ok,
        "digest_path": str(digest_path),
        "prefix": prefix,
        "categories": len(categories),
        "stories": sum(len(c.get("stories") or []) for c in categories),
        "librarian_entries": len(entries),
        "warnings": warnings,
    }
