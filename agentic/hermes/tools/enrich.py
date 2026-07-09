"""LLM enrichment for agentic librarian + synthesizer artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llm_pipeline.editorial import load_editorial_brief
from llm_pipeline.llm_client import make_client, make_raw_chat
from llm_pipeline.schema import CategoryStories, DigestHeader

from tools.artifacts import (
    LIBRARIAN_ARTIFACT,
    _read_research_output,
    _research_topic,
    validate_librarian_artifact,
)
from tools.showcase import RESEARCH_CATEGORY_IDS


@dataclass
class EnrichResult:
    applied: bool
    warnings: list[str] = field(default_factory=list)


def enrich_cfg(repo_cfg: dict[str, Any], roles: dict[str, Any]) -> dict[str, Any] | None:
    """Return LLM config for agentic enrich, or None if disabled."""
    ae = roles.get("agentic_enrich") or {}
    if ae.get("enabled") is False:
        return None
    if not (repo_cfg.get("llm") or {}).get("enabled", True):
        return None
    cfg = json.loads(json.dumps(repo_cfg))
    model = ae.get("model")
    if model:
        cfg["llm"]["model"] = model
    return cfg


def _llm_call(client: Any, model: str, max_retries: int, prompt: str, response_model: type) -> Any:
    from llm_pipeline.diagnostics import instrumented_llm_call

    return instrumented_llm_call(
        client, model, max_retries, prompt, response_model, call_name="agentic.enrich"
    )


def enrich_librarian_md(
    workspace: Path,
    research_rows: list[dict[str, Any]],
    cfg: dict[str, Any],
    *,
    prefix: str | None = None,
    hermes_home: Path | None = None,
) -> EnrichResult:
    """Rewrite librarian.md with LLM merge narrative. Keeps deterministic on failure."""
    path = workspace / LIBRARIAN_ARTIFACT
    if not path.is_file():
        return EnrichResult(False, ["librarian enrich skipped: missing librarian.md"])

    deterministic = path.read_text(encoding="utf-8")
    home = hermes_home or Path.home() / ".hermes"
    chunks: list[str] = []
    for row in research_rows:
        topic = _research_topic(str(row.get("title", "")))
        text = _read_research_output(row, prefix=prefix, hermes_home=home)
        if not text:
            continue
        chunks.append(f"### Research: {topic}\n{text}")

    if not chunks:
        return EnrichResult(False, ["librarian enrich skipped: no research chunks"])

    try:
        chat, _model = make_raw_chat(cfg)
    except SystemExit:
        return EnrichResult(False, ["librarian enrich skipped: LLM client unavailable"])

    prompt = f"""You are the AI Digest Librarian. Merge these parallel researcher outputs into
one librarian.md for the Synthesizer. Use markdown with:
- # Librarian: merge & classify
- ## Executive merge (2-4 sentences)
- ## Topics applied (bullet list)
- ## Merged by category (subsection per topic, deduped bullets with URLs preserved)
- ## Graph sketch (feeds_topic / related_to bullets)

Keep every URL from the inputs. Do not invent links.

{chr(10).join(chunks)}
"""
    try:
        md = chat([{"role": "user", "content": prompt}]).strip()
    except Exception as exc:
        path.write_text(deterministic, encoding="utf-8")
        return EnrichResult(False, [f"librarian enrich failed: {exc}"])

    if len(md) < 100 or "http" not in md:
        path.write_text(deterministic, encoding="utf-8")
        return EnrichResult(False, ["librarian enrich failed: output too short or missing URLs"])

    if md.lower().startswith("here is"):
        parts = md.split("\n", 1)
        md = parts[1].strip() if len(parts) > 1 else md

    path.write_text(md + "\n", encoding="utf-8")
    if validate_librarian_artifact(workspace):
        path.write_text(deterministic, encoding="utf-8")
        return EnrichResult(False, ["librarian enrich failed: enriched artifact did not pass gate"])
    return EnrichResult(True)


def enrich_digest_json(digest: dict[str, Any], cfg: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """LLM-polish research-touched categories and executive summary."""
    warnings: list[str] = []
    try:
        client, model, max_retries = make_client(cfg)
    except SystemExit:
        return digest, ["digest enrich skipped: LLM client unavailable"]

    brief = load_editorial_brief()
    categories = digest.get("categories") or []

    for cat in categories:
        cid = cat.get("id")
        if cid not in RESEARCH_CATEGORY_IDS:
            continue
        stories = cat.get("stories") or []
        if not stories:
            continue
        prompt = f"""{brief}

## Task
Enrich stories for category **{cat.get('label')}** (`{cid}`).
Keep every story `id` and `url` exactly. Rewrite `title`, `summary`, scores (1-5), and `tags`.
Summaries: 2-3 sentences, magazine quality. No em dashes.

## Input stories
{json.dumps(stories, indent=2)[:12000]}

Return JSON with stories array only."""
        try:
            enriched = _llm_call(client, model, max_retries, prompt, CategoryStories)
            cat["stories"] = [s.model_dump() for s in enriched.stories]
            for s in cat["stories"]:
                s["provenance"] = f"agent:researcher:{cid}"
        except Exception as exc:
            warnings.append(f"digest enrich category {cid} failed: {exc}")

    titles: list[str] = []
    for cat in categories:
        for story in cat.get("stories") or []:
            titles.append(str(story.get("title") or ""))
    title_sample = "; ".join(t for t in titles[:8] if t)
    summary_prompt = f"""{brief}

## Task
Write one executive takeaway sentence for today's AI digest (like production digests).
Stories today include: {title_sample}

Return JSON with summary field only."""
    try:
        header = _llm_call(client, model, max_retries, summary_prompt, DigestHeader)
        digest["summary"] = header.summary
        if header.aisearch_video_url:
            digest["aisearch_video_url"] = header.aisearch_video_url
        if header.aisearch_video_label:
            digest["aisearch_video_label"] = header.aisearch_video_label
    except Exception as exc:
        warnings.append(f"digest enrich summary failed: {exc}")

    return digest, warnings
