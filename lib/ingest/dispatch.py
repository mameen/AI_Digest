"""Dispatch — topic id → registry binding → generic extractors (+ optional web fallback)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.ingest.lazy import materialize_binding_cache
from lib.ingest.compose import compose_bullets
from lib.ingest.markdown import write_research_markdown
from lib.ingest.topics.registry import binding_for
from lib.ingest.types import TopicResearch


def research_topic(cfg: dict[str, Any], prefix: str, topic: str) -> TopicResearch:
    """Materialize raw bullets for a topic via generic extractors (deterministic seed path)."""
    key = topic.strip().lower()
    binding = binding_for(key)
    if binding is None:
        return TopicResearch(
            topic=key,
            bullets=[],
            seed="unknown topic — no registry binding",
            preflight_prefix=prefix,
        )

    import lib.ingest.bundle as bundle_mod

    if prefix in bundle_mod._CACHE:
        bundle = bundle_mod._CACHE[prefix]
    else:
        bundle = materialize_binding_cache(cfg, prefix, binding)
    bullets, seed = compose_bullets(cfg, bundle, binding)
    if len(bullets) < 3:
        return TopicResearch(
            topic=key,
            bullets=bullets,
            seed=f"{seed} (sparse — need ≥3 bullets)",
            preflight_prefix=bundle.prefix,
        )
    return TopicResearch(
        topic=key,
        bullets=bullets,
        seed=seed,
        preflight_prefix=bundle.prefix,
    )


def seed_topic_workspace(
    topic: str,
    workspace: Path,
    *,
    cfg: dict[str, Any],
    prefix: str,
) -> dict[str, Any]:
    """Write output.md via compose — test/helper only; workers use tools + LLM."""
    result = research_topic(cfg, prefix, topic)
    if len(result.bullets) < 3:
        return {
            "ok": False,
            "topic": topic,
            "error": "fewer than 3 verified bullets",
            "seed": result.seed,
            "bullets": len(result.bullets),
        }
    out_path = write_research_markdown(topic, workspace, result.bullets)
    return {
        "ok": True,
        "path": str(out_path),
        "topic": topic,
        "bullets": len(result.bullets),
        "verified_urls": sum(1 for b in result.bullets if b.verified),
        "seed": result.seed,
        "preflight_prefix": result.preflight_prefix,
    }
