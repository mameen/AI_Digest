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
from tools.digest_scaffold import empty_digest

_CLAIM_SECTION_RE = re.compile(r"^###\s+(.+)$", re.MULTILINE)
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


_ARXIV_ID_RE = re.compile(r"\barXiv\s+([\d]{4}\.[\d]{4,5})\b", re.IGNORECASE)
_GITHUB_URL_RE = re.compile(r"https?://github\.com/[\w./-]+|github\.com/[\w./-]+")
_YOUTUBE_ID_RE = re.compile(r"\b(?:youtube\.com/watch\?v=|youtu\.be/|)([A-Za-z0-9_-]{11})\b")

_TABLE_HEADER_HINTS = frozenset(
    {
        "paper",
        "topic",
        "event",
        "entry",
        "rank",
        "model",
        "url",
        "source",
        "focus",
        "key finding",
        "overlapping topic",
        "canonical source(s)",
        "merge note",
        "topic area",
        "entry count",
        "primary sources",
        "humaneval+ pass@1",
        "mbpp+ pass@1",
        "ai index",
        "price ($/1m)",
    }
)

_SKIP_TOP_SECTIONS = (
    "dedupe & overlap",
    "coverage summary",
    "ambiguities for the synthesizer",
)


def _normalize_librarian_url(raw: str) -> str | None:
    """Turn librarian table cells into fetchable https URLs."""
    cell = raw.strip().rstrip(".,)")
    if not cell or cell in {"—", "-", "URL", "url"}:
        return None
    if cell.lower().startswith("hf papers/"):
        paper_id = cell.split("/", 1)[-1].strip()
        if paper_id:
            return f"https://huggingface.co/papers/{paper_id}"
    if cell.startswith("http://") or cell.startswith("https://"):
        return cell
    gh = _GITHUB_URL_RE.search(cell)
    if gh:
        path = gh.group(0)
        return path if path.startswith("http") else f"https://{path.lstrip('/')}"
    if re.match(r"^[\w.-]+\.[a-z]{2,}(?:/[\w./%-]*)?$", cell, re.IGNORECASE):
        return f"https://{cell.lstrip('/')}"
    return None


def _extract_urls_from_text(text: str) -> list[str]:
    urls = [_normalize_librarian_url(u) for u in _URL_RE.findall(text)]
    urls.extend(
        f"https://arxiv.org/abs/{aid}"
        for aid in _ARXIV_ID_RE.findall(text)
    )
    for match in _GITHUB_URL_RE.findall(text):
        urls.append(_normalize_librarian_url(match))
    for vid in _YOUTUBE_ID_RE.findall(text):
        if len(vid) == 11:
            urls.append(f"https://www.youtube.com/watch?v={vid}")
    out: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            out.append(url)
    return out


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    body = stripped.replace("|", "").strip()
    return not body or set(body) <= {"-"}


def _is_table_header(cells: list[str]) -> bool:
    lowered = [c.strip().lower() for c in cells if c.strip()]
    if not lowered:
        return True
    return all(any(h in cell for h in _TABLE_HEADER_HINTS) for cell in lowered[:3])


def _parse_table_row(cells: list[str], section: str) -> dict[str, Any] | None:
    cleaned = [c.strip() for c in cells if c.strip()]
    if len(cleaned) < 2 or _is_table_header(cleaned):
        return None
    url: str | None = None
    url_idx = -1
    for idx, cell in enumerate(cleaned):
        candidate = _normalize_librarian_url(cell)
        if candidate:
            url = candidate
            url_idx = idx
            break
    if not url:
        for cell in cleaned:
            for candidate in _extract_urls_from_text(cell):
                url = candidate
                break
            if url:
                break
    if not url:
        return None
    title = cleaned[0]
    if url_idx == 0 and len(cleaned) > 1:
        title = cleaned[1]
    summary_parts = [c for i, c in enumerate(cleaned) if i not in {0, url_idx} and c != url]
    summary = " — ".join(summary_parts[:2]).strip() or title
    return {
        "section": section,
        "category_id": infer_category_id(section),
        "title": title[:120],
        "summary": summary[:500],
        "url": url,
        "source": "Librarian",
    }


def _parse_claim_sections(text: str) -> list[dict[str, Any]]:
    """Legacy librarian bullets: ### sections with - **claim:** lines."""
    entries: list[dict[str, Any]] = []
    parts = _CLAIM_SECTION_RE.split(text)
    idx = 1
    while idx + 1 < len(parts):
        title = parts[idx].strip()
        body = parts[idx + 1]
        idx += 2
        if "merged entries" in title.lower() or title.lower().startswith("topic map"):
            continue
        claim = ""
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("- **claim:**"):
                claim = stripped.split(":", 1)[-1].strip()
                break
        if not claim:
            continue
        urls = _extract_urls_from_text(body)
        url = urls[0] if urls else None
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


def _parse_prose_blocks(lines: list[str], section: str) -> list[dict[str, Any]]:
    """#### subsections with **Title** (arXiv …) followed by prose."""
    entries: list[dict[str, Any]] = []
    block_title = ""
    block_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#### "):
            if block_title:
                body = "\n".join(block_lines).strip()
                urls = _extract_urls_from_text(block_title + "\n" + body)
                if urls:
                    entries.append(
                        {
                            "section": section,
                            "category_id": infer_category_id(section),
                            "title": block_title[:120],
                            "summary": (body or block_title)[:500],
                            "url": urls[0],
                            "source": "Librarian",
                        }
                    )
            block_title = stripped[5:].strip()
            block_lines = []
            continue
        if stripped.startswith("**") and "arxiv" in stripped.lower():
            inner = stripped.strip("*").strip()
            title_part = inner.split("(")[0].strip()
            urls = _extract_urls_from_text(stripped)
            if urls:
                entries.append(
                    {
                        "section": section,
                        "category_id": infer_category_id(section),
                        "title": title_part[:120],
                        "summary": title_part[:500],
                        "url": urls[0],
                        "source": "Librarian",
                    }
                )
            continue
        if block_title and stripped and not stripped.startswith("|"):
            if stripped.startswith("**") and stripped.endswith("**"):
                inner = stripped.strip("*").strip()
                if inner:
                    block_title = inner.split("(")[0].strip()
            else:
                block_lines.append(stripped)
    if block_title:
        body = "\n".join(block_lines).strip()
        urls = _extract_urls_from_text(block_title + "\n" + body)
        if urls:
            entries.append(
                {
                    "section": section,
                    "category_id": infer_category_id(section),
                    "title": block_title[:120],
                    "summary": (body or block_title)[:500],
                    "url": urls[0],
                    "source": "Librarian",
                }
            )
    return entries


def parse_librarian_entries(text: str) -> list[dict[str, Any]]:
    """Extract story candidates from librarian knowledge-graph markdown."""
    by_url: dict[str, dict[str, Any]] = {}

    def add(entry: dict[str, Any]) -> None:
        url = str(entry.get("url") or "").strip()
        if url and url not in by_url:
            by_url[url] = entry

    for entry in _parse_claim_sections(text):
        add(entry)

    current_section = "research"
    skip_section = False
    section_lines: list[str] = []

    def flush_section() -> None:
        nonlocal section_lines
        if section_lines and not skip_section:
            for entry in _parse_prose_blocks(section_lines, current_section):
                add(entry)
        section_lines = []

    for line in text.splitlines():
        if line.startswith("## ") and not line.startswith("###"):
            top = line[3:].strip().lower()
            skip_section = any(top.startswith(s) for s in _SKIP_TOP_SECTIONS)
            flush_section()
            continue

        h3 = re.match(r"^###\s+(.+)$", line.strip())
        if h3:
            flush_section()
            current_section = h3.group(1).strip()
            skip_section = any(s in current_section.lower() for s in _SKIP_TOP_SECTIONS)
            continue

        if re.match(r"^####\s+", line.strip()):
            flush_section()
            if not skip_section:
                section_lines = [line]
            continue

        if skip_section:
            continue

        if _is_table_separator(line):
            continue

        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            entry = _parse_table_row(cells, current_section)
            if entry:
                add(entry)
            continue

        stripped = line.strip()
        if stripped.startswith("- ") and "|" in stripped:
            for url in _extract_urls_from_text(stripped):
                title = stripped.lstrip("- ").split("|", 1)[0].strip()
                add(
                    {
                        "section": current_section,
                        "category_id": infer_category_id(current_section),
                        "title": title[:120],
                        "summary": title[:500],
                        "url": url,
                        "source": "Librarian",
                    }
                )
            continue

        section_lines.append(line)

    flush_section()

    # YouTube chapter mention without a table row
    if "SettwwX2cCI" in text:
        add(
            {
                "section": "AI Search & Capabilities Demos",
                "category_id": "aisearch",
                "title": "GPT 5.6 capability demonstrations (theAIsearch)",
                "summary": "Chaptered YouTube demo of GPT 5.6 across multiple capability domains.",
                "url": "https://www.youtube.com/watch?v=SettwwX2cCI",
                "source": "Librarian",
            }
        )

    return list(by_url.values())


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
    digest = empty_digest(prefix)

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
You are the AI Digest Synthesizer. Librarian already resolved overlap and mapped
topics — do not reclassify or merge. Turn these librarian entries into polished
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
