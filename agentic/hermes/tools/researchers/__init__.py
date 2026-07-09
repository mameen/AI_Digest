"""Topic-specific researcher seeders — thin Hermes wrappers over lib.ingest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.ingest.dispatch import seed_topic_workspace

from tools.researchers import aisearch, leaderboard, youtube
from tools.researchers.ingest import warm_ingest_cache

SeedFn = type(aisearch.seed)

TOPIC_SEEDERS: dict[str, SeedFn] = {
    "aisearch": aisearch.seed,
    "leaderboard": leaderboard.seed,
    "youtube": youtube.seed,
}


def seed_topic(
    topic: str,
    workspace: Path,
    *,
    cfg: dict[str, Any] | None = None,
    prefix: str | None = None,
) -> dict[str, Any]:
    """Test/eval helper only — not registered on worker toolsets."""
    from lib.ingest.topics.registry import binding_for

    key = topic.strip().lower()
    binding = binding_for(key)
    if cfg is None or not prefix:
        from datetime import datetime, timezone

        from tools.baseline import default_config

        cfg = cfg or default_config()
        prefix = prefix or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    if binding and binding.evaluation:
        return seed_topic_workspace(topic, workspace, cfg=cfg, prefix=prefix)

    if key in TOPIC_SEEDERS:
        warm_ingest_cache(cfg, prefix)
        return seed_topic_workspace(topic, workspace, cfg=cfg, prefix=prefix)

    return {
        "ok": False,
        "topic": key,
        "error": (
            f"no test seeder for {key!r} — live workers must use digest tools + LLM; "
            "only evaluation_test_topic may use committed fixtures in eval runs"
        ),
    }


__all__ = ["TOPIC_SEEDERS", "seed_topic", "warm_ingest_cache"]
