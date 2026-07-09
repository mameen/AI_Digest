"""
Configuration loader for ``config.yaml``, optional ``.env``, and LLM defaults.

The pipeline defaults to **local Ollama** (see ``config.yaml`` → ``llm``).
Override via environment or edit config before running ``run.py``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from lib.paths import LLM_PIPELINE_ROOT, REPO_ROOT


def _default_llm() -> dict[str, Any]:
    """Sensible local defaults when no external preference file exists."""
    return {
        "provider": "ollama",
        "model": "llama3.1:latest",
        "base_url": "http://localhost:11434/v1",
    }


def _apply_llm_defaults(cfg: dict[str, Any]) -> None:
    defaults = _default_llm()
    llm = cfg.setdefault("llm", {})
    for key in ("provider", "model", "base_url"):
        llm.setdefault(key, defaults[key])


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load YAML config and merge optional ``.env`` key/value pairs."""
    cfg_path = path or (LLM_PIPELINE_ROOT / "config.yaml")
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    _apply_llm_defaults(cfg)

    env_path = REPO_ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

    return cfg
