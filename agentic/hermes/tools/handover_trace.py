"""Provenance trace for agentic handover receipts — auditable source chain."""

from __future__ import annotations

import re
from typing import Any

from lib.paths import LLM_PIPELINE_ROOT

from tools.artifacts import DIGEST_ARTIFACT, LIBRARIAN_ARTIFACT
from tools.runtime_store import RUNTIME_ROOT, load_digest, load_research_text
from tools.showcase import _BASELINE_PREFIX
from lib.ingest.compose import seed_for_binding
from lib.ingest.topics.registry import binding_for

from tools.topics import load_demo_topics


def _topic_seed(topic: str) -> str:
    binding = binding_for(topic)
    if binding is None:
        return "unknown topic"
    return seed_for_binding(binding)


def extract_urls(text: str) -> list[str]:
    """Pull http(s) URLs from markdown bullet lines."""
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"https?://[^\s\)>\"%]+", text):
        url = match.group(0).rstrip("%C2%A0")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _baseline_source() -> dict[str, Any]:
    pinned = LLM_PIPELINE_ROOT / "reports" / f"{_BASELINE_PREFIX}.json"
    return {
        "kind": "carry-forward",
        "prefix": _BASELINE_PREFIX,
        "path": str(pinned),
        "exists": pinned.is_file(),
        "categories": f"{12 - len(load_demo_topics())} carry-forward categories",
    }


def _research_trace(prefix: str) -> list[dict[str, Any]]:
    run_dir = RUNTIME_ROOT / prefix
    rel = RUNTIME_ROOT.parent
    rows: list[dict[str, Any]] = []
    for topic in load_demo_topics():
        cache = run_dir / "research" / f"{topic}.md"
        text = load_research_text(prefix, topic)
        rows.append(
            {
                "topic": topic,
                "category_id": topic,
                "seed": _topic_seed(topic),
                "artifact": str(cache.relative_to(rel)) if cache.is_file() else str(cache),
                "cached": cache.is_file(),
                "urls": extract_urls(text) if text else [],
            }
        )
    return rows


def _digest_provenance_summary(digest: dict[str, Any]) -> dict[str, Any]:
    by_category: dict[str, dict[str, int]] = {}
    totals: dict[str, int] = {}
    for cat in digest.get("categories") or []:
        cid = str(cat.get("id") or "")
        if not cid:
            continue
        counts: dict[str, int] = {}
        for story in cat.get("stories") or []:
            prov = str(story.get("provenance") or "unknown")
            counts[prov] = counts.get(prov, 0) + 1
            totals[prov] = totals.get(prov, 0) + 1
        by_category[cid] = counts
    return {"by_category": by_category, "totals": totals}


def build_handover_trace(prefix: str) -> dict[str, Any]:
    """Trace information sources for a completed handover run."""
    run_dir = RUNTIME_ROOT / prefix
    rel = RUNTIME_ROOT.parent
    digest = load_digest(prefix)
    research = _research_trace(prefix)
    return {
        "graph": "research × N → librarian → synthesizer",
        "baseline": _baseline_source(),
        "research": research,
        "librarian": {
            "artifact": str((run_dir / LIBRARIAN_ARTIFACT).relative_to(rel))
            if (run_dir / LIBRARIAN_ARTIFACT).is_file()
            else str(run_dir / LIBRARIAN_ARTIFACT),
            "inputs": [r["topic"] for r in research if r.get("cached")],
            "merge": "deterministic concat of research output.md",
        },
        "synthesizer": {
            "artifact": str((run_dir / DIGEST_ARTIFACT).relative_to(rel))
            if (run_dir / DIGEST_ARTIFACT).is_file()
            else str(run_dir / DIGEST_ARTIFACT),
            "assembly": "synthesize_digest (LLM) + baseline carry-forward",
            "digest_provenance": _digest_provenance_summary(digest) if digest else {},
        },
    }


def format_trace_summary(trace: dict[str, Any]) -> list[str]:
    """Human-readable provenance lines for CLI output."""
    lines: list[str] = []
    baseline = trace.get("baseline") or {}
    lines.append(
        f"  baseline: {baseline.get('path')} (prefix {baseline.get('prefix')})"
    )
    for row in trace.get("research") or []:
        n = len(row.get("urls") or [])
        lines.append(
            f"  research/{row.get('topic')}: {n} url(s) via {row.get('seed')}"
        )
    lib = trace.get("librarian") or {}
    lines.append(f"  librarian: merged {len(lib.get('inputs') or [])} research topics")
    syn = trace.get("synthesizer") or {}
    totals = (syn.get("digest_provenance") or {}).get("totals") or {}
    if totals:
        parts = ", ".join(f"{k}={v}" for k, v in sorted(totals.items()))
        lines.append(f"  synthesizer provenance: {parts}")
    return lines
