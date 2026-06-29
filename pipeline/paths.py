"""
Project path layout for the standalone AI Digest pipeline.

Committed demo archives live in ``reports/`` and ``diagnostics/`` (GitHub Pages).
Ephemeral fetch cache uses ``.cache/`` (gitignored). ``.preflight/``, ``reports/``, and ``diagnostics/`` are tracked.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

VENDOR_DIR = PROJECT_ROOT / "vendor" / "ai-news-digest"
SKILL_SCRIPTS = VENDOR_DIR / "scripts"
SKILL_DIR = VENDOR_DIR


def _resolve_dir(relative: str) -> Path:
    """Resolve a repo-relative directory and ensure it exists."""
    path = (PROJECT_ROOT / relative).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def reports_dir(cfg: dict) -> Path:
    rel = (cfg.get("output") or {}).get("reports_dir", "reports")
    return _resolve_dir(rel)


def cache_dir(cfg: dict) -> Path:
    rel = (cfg.get("output") or {}).get("cache_dir", ".cache")
    return _resolve_dir(rel)


def preflight_dir(cfg: dict) -> Path:
    rel = (cfg.get("output") or {}).get("preflight_dir", ".preflight")
    return _resolve_dir(rel)


def diagnostics_dir(cfg: dict) -> Path:
    rel = (cfg.get("diagnostics") or {}).get("output_dir", "diagnostics")
    return _resolve_dir(rel)
