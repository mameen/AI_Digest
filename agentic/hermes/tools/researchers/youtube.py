"""Hermes wrapper — delegates to lib.ingest (youtube preflight category)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lib.ingest import youtube as _lib_youtube
from lib.ingest.dispatch import seed_topic_workspace

SEED = _lib_youtube.SEED


def seed(
    topic: str,
    workspace: Path,
    *,
    cfg: dict[str, Any],
    prefix: str,
) -> dict[str, Any]:
    return seed_topic_workspace(topic, workspace, cfg=cfg, prefix=prefix)
