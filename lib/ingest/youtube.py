"""Backward-compat shim — youtube secondary channels via preflight skeleton."""

from __future__ import annotations

from lib.ingest.compose import research_from_binding, seed_for_binding
from lib.ingest.topics.registry import TOPIC_BINDINGS

_BINDING = TOPIC_BINDINGS["youtube"]
SEED = seed_for_binding(_BINDING)


def research(cfg, bundle):  # noqa: ANN001
    return research_from_binding(cfg, bundle, _BINDING)
