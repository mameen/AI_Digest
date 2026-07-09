"""Backward-compat shim — leaderboard uses crawl + structured extractors via registry."""

from __future__ import annotations

from typing import Any

from lib.ingest.compose import compose_bullets, research_from_binding, seed_for_binding
from lib.ingest.topics.registry import TOPIC_BINDINGS
from lib.ingest.types import IngestBundle, ResearchBullet, TopicResearch

_BINDING = TOPIC_BINDINGS["leaderboard"]
SEED = seed_for_binding(_BINDING)


def bullets_from_bundle(cfg: dict[str, Any], bundle: IngestBundle) -> list[ResearchBullet]:
    bullets, _ = compose_bullets(cfg, bundle, _BINDING)
    return bullets


def research(cfg: dict[str, Any], bundle: IngestBundle) -> TopicResearch:
    return research_from_binding(cfg, bundle, _BINDING)
