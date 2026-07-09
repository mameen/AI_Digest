"""
Path layout for the staged digest pipeline.

Committed demo archives live under ``LLM_PIPELINE_ROOT`` (``reports/``,
``diagnostics/``). Ephemeral fetch cache uses ``.cache/`` (gitignored).
Vendor skill scripts stay at ``REPO_ROOT/vendor/`` until a later layout pass.
"""

from __future__ import annotations

from pathlib import Path

from lib.paths import AGENTIC_ROOT, LLM_PIPELINE_ROOT, REPO_ROOT, WEB_ROOT

VENDOR_DIR = LLM_PIPELINE_ROOT / "vendor" / "ai-news-digest"
SKILL_SCRIPTS = VENDOR_DIR / "scripts"
SKILL_DIR = VENDOR_DIR

__all__ = [
    "AGENTIC_ROOT",
    "LLM_PIPELINE_ROOT",
    "REPO_ROOT",
    "WEB_ROOT",
    "VENDOR_DIR",
    "SKILL_SCRIPTS",
    "SKILL_DIR",
    "cache_dir",
    "diagnostics_dir",
    "output_root",
    "preflight_dir",
    "reports_dir",
]


def _resolve_dir(relative: str, *, base: Path = LLM_PIPELINE_ROOT) -> Path:
    """Resolve a path relative to *base* and ensure it exists."""
    path = (base / relative).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def output_root(cfg: dict) -> Path:
    """Published reports/diagnostics root — staged pipeline unless ``output.root`` is set."""
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
