"""Hermes wrapper — delegates to lib.ingest."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.ingest import leaderboard as _lib_leaderboard
from lib.ingest.dispatch import seed_topic_workspace

SEED = _lib_leaderboard.SEED


def seed(
    topic: str,
    workspace: Path,
    *,
    cfg: dict[str, Any],
    prefix: str,
) -> dict[str, Any]:
    return seed_topic_workspace(topic, workspace, cfg=cfg, prefix=prefix)
