"""Configuration loader for ``config.yaml``, optional ``.env``, and LLM defaults.

The pipeline defaults to **local Ollama** (see ``config.yaml`` → ``llm``).
Override via environment or edit config before running ``run.py``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from lib.paths import LLM_PIPELINE_ROOT, REPO_ROOT


class Config:
    """Immutable configuration loaded from ``config.yaml`` + optional ``.env``."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self._apply_llm_defaults()

    @property
    def llm(self) -> dict[str, Any]:
        return self._data.get("llm", {})

    @property
    def raw(self) -> dict[str, Any]:
        return self._data

    def _apply_llm_defaults(self) -> None:
        defaults = Config._default_llm()
        llm = self._data.setdefault("llm", {})
        for key in ("provider", "model", "base_url"):
            llm.setdefault(key, defaults[key])

    @staticmethod
    def _default_llm() -> dict[str, Any]:
        return {
            "provider": "ollama",
            "model": "llama3.1:latest",
            "base_url": "http://localhost:11434/v1",
        }

    @staticmethod
    def _load_env(repo_root: Path) -> None:
        env_path = repo_root / ".env"
        if not env_path.is_file():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load YAML config and merge optional ``.env`` key/value pairs."""
    cfg_path = path or (LLM_PIPELINE_ROOT / "config.yaml")
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    Config._load_env(REPO_ROOT)

    # Apply LLM defaults
    defaults = Config._default_llm()
    llm = cfg.setdefault("llm", {})
    for key in ("provider", "model", "base_url"):
        llm.setdefault(key, defaults[key])

    return cfg


# Backwards-compatible helpers (used by tests)
_default_llm = Config._default_llm  # noqa: F405
_apply_llm_defaults = None  # replaced below for compat


def _apply_llm_defaults(cfg: dict[str, Any]) -> None:
    """Apply LLM defaults to a mutable config dict (legacy compat)."""
    defaults = _default_llm()
    llm = cfg.setdefault("llm", {})
    for key in ("provider", "model", "base_url"):
        llm.setdefault(key, defaults[key])
