"""Backward-compat shim — aisearch is a registry binding, not a bespoke composer."""

from __future__ import annotations

from typing import Any

from lib.ingest.compose import research_from_binding, seed_for_binding
from lib.ingest.extractors.preflight import bullets_from_category
from lib.ingest.topics.registry import TOPIC_BINDINGS
from lib.ingest.types import IngestBundle, ResearchBullet, TopicResearch

_BINDING = TOPIC_BINDINGS["aisearch"]
SEED = seed_for_binding(_BINDING)


def bullets_from_preflight(preflight: dict[str, Any]) -> list[ResearchBullet]:
    return bullets_from_category(preflight, "aisearch")


def research(cfg: dict[str, Any], bundle: IngestBundle) -> TopicResearch:
    return research_from_binding(cfg, bundle, _BINDING)
