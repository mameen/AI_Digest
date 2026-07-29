"""
Repository path constants and cfg-dependent directory resolvers.

Constants (no config needed):
    REPO_ROOT        - git checkout root
    LLM_PIPELINE_ROOT - staged digest runner + published archives
    WEB_ROOT         - GitHub Pages artifact (``app/``)
    AGENTIC_ROOT     - Hermes POC tree
    LIB_DIR          - shared library directory

Cfg-dependent resolvers (used by pipeline stages):
    cache_dir(cfg), preflight_dir(cfg), reports_dir(cfg), diagnostics_dir(cfg)
    output_root(cfg) - published reports/diagnostics root
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


# Constants (module-level, evaluated at import time)

REPO_ROOT = _find_repo_root()
_paths = _load_paths(REPO_ROOT)

LLM_PIPELINE_ROOT = (REPO_ROOT / _paths["llm_pipeline_root"]).resolve()
WEB_ROOT = (REPO_ROOT / _paths["web_root"]).resolve()
AGENTIC_ROOT = (REPO_ROOT / _paths["agentic_root"]).resolve()
LIB_DIR = (REPO_ROOT / _paths["lib"]).resolve()

# Derived constants

VENDOR_DIR = LLM_PIPELINE_ROOT / "vendor" / "ai-news-digest"
SKILL_SCRIPTS = VENDOR_DIR / "scripts"
SKILL_DIR = VENDOR_DIR

__all__ = [
    # Constants
    "REPO_ROOT",
    "LLM_PIPELINE_ROOT",
    "WEB_ROOT",
    "AGENTIC_ROOT",
    "LIB_DIR",
    "VENDOR_DIR",
    "SKILL_SCRIPTS",
    "SKILL_DIR",
    # Cfg-dependent resolvers
    "cache_dir",
    "diagnostics_dir",
    "output_root",
    "preflight_dir",
    "reports_dir",
]


# Cfg-dependent resolvers


def _resolve_dir(relative: str, *, base: Path = LLM_PIPELINE_ROOT) -> Path:
    """Resolve a path relative to *base* and ensure it exists."""
    path = (base / relative).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_root(cfg: dict) -> Path:
    """Published reports/diagnostics root - staged pipeline unless ``output.root`` is set."""
    rel = (cfg.get("output") or {}).get("root")
    if not rel:
        return LLM_PIPELINE_ROOT
    path = Path(str(rel))
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def reports_dir(cfg: dict) -> Path:
    rel = (cfg.get("output") or {}).get("reports_dir", "reports")
    return _resolve_dir(rel, base=output_root(cfg))


def cache_dir(cfg: dict) -> Path:
    rel = (cfg.get("output") or {}).get("cache_dir", ".cache")
    return _resolve_dir(rel)


def preflight_dir(cfg: dict) -> Path:
    rel = (cfg.get("output") or {}).get("preflight_dir", ".preflight")
    return _resolve_dir(rel)


def diagnostics_dir(cfg: dict) -> Path:
    rel = (cfg.get("diagnostics") or {}).get("output_dir", "diagnostics")
    diag_root = (cfg.get("diagnostics") or {}).get("root")
    if diag_root:
        base = Path(str(diag_root))
        if not base.is_absolute():
            base = (REPO_ROOT / base).resolve()
        else:
            base = base.resolve()
    else:
        base = output_root(cfg)
    return _resolve_dir(rel, base=base)
