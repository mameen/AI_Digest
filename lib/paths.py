"""
Repository path constants.

REPO_ROOT        — git checkout root
LLM_PIPELINE_ROOT — staged digest runner + published archives
WEB_ROOT         — GitHub Pages artifact (``app/`` — populated by ``scripts/deploy_app.py``)
AGENTIC_ROOT     — Hermes POC tree
"""

from __future__ import annotations

from pathlib import Path

import yaml

_DEFAULTS = {
    "llm_pipeline_root": "llm_pipeline",
    "web_root": "app",
    "agentic_root": "agentic/hermes",
    "lib": "lib",
}


def _find_repo_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in (here, *here.parents):
        if (candidate / "config" / "paths.yaml").is_file():
            return candidate
        if (candidate / ".git").is_dir():
            return candidate
    return here.parent


def _load_paths(repo_root: Path) -> dict[str, str]:
    cfg_path = repo_root / "config" / "paths.yaml"
    if not cfg_path.is_file():
        return dict(_DEFAULTS)
    with cfg_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    merged = dict(_DEFAULTS)
    merged.update((data.get("paths") or data))
    return merged


REPO_ROOT = _find_repo_root()
_paths = _load_paths(REPO_ROOT)

LLM_PIPELINE_ROOT = (REPO_ROOT / _paths["llm_pipeline_root"]).resolve()
WEB_ROOT = (REPO_ROOT / _paths["web_root"]).resolve()
AGENTIC_ROOT = (REPO_ROOT / _paths["agentic_root"]).resolve()
LIB_DIR = (REPO_ROOT / _paths["lib"]).resolve()
