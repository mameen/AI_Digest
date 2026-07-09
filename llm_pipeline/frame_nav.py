"""Top-right cross-link between digest archive, diagnostics, and admin."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from lib.paths import LLM_PIPELINE_ROOT

FrameView = Literal["reports", "diagnostics", "admin"]

REPORTS_INDEX = "../reports/index.html"
DIAGNOSTICS_INDEX = "../diagnostics/index.html"
ADMIN_INDEX = "../admin/index.html"
DIAGNOSTICS_ICON = "⏱️"


def diagnostics_available(cfg: dict[str, Any] | None = None, diag_dir: Path | None = None) -> bool:
    if diag_dir is not None:
        return any(diag_dir.glob("*.diagnostics.json"))
    if cfg is None:
        from llm_pipeline.config import load_config

        cfg = load_config()
    from llm_pipeline.paths import diagnostics_dir

    return any(diagnostics_dir(cfg).glob("*.diagnostics.json"))


def admin_nav_enabled(cfg: dict[str, Any] | None = None, admin_dir: Path | None = None) -> bool:
    """Admin ⚙️ nav link — off until ``site.admin_nav_enabled`` (local server WIP)."""
    if cfg is None:
        from llm_pipeline.config import load_config

        cfg = load_config()
    if not (cfg.get("site") or {}).get("admin_nav_enabled", False):
        return False
    if admin_dir is None:
        admin_dir = LLM_PIPELINE_ROOT / "server"
    return (admin_dir / "index.html").is_file()


def frame_nav_css() -> str:
    """Nav chrome lives in frame.css; kept for callers that inject CSS separately."""
    return ""


def frame_controls_html(
    view: FrameView,
    *,
    diagnostics_available: bool = False,
    admin_available: bool = False,
) -> str:
    nav = frame_nav_html(
        view,
        diagnostics_available=diagnostics_available,
        admin_available=admin_available,
    )
    return f'<div class="frame-controls">{nav}</div>'


def frame_nav_html(
    view: FrameView,
    *,
    diagnostics_available: bool = False,
    admin_available: bool = False,
) -> str:
    """📰 reports · ⏱️ diagnostics · ⚙️ admin (current view omitted)."""
    links: list[str] = []
    if view != "reports":
        links.append(f'<a href="{REPORTS_INDEX}" title="Digest archive">📰</a>')
    if view != "diagnostics" and diagnostics_available:
        links.append(
            f'<a href="{DIAGNOSTICS_INDEX}" title="Pipeline diagnostics">{DIAGNOSTICS_ICON}</a>'
        )
    if view != "admin" and admin_available:
        links.append(f'<a href="{ADMIN_INDEX}" title="Control admin">⚙️</a>')
    if not links:
        return ""
    return f'<nav class="frame-nav" aria-label="Switch view">{"".join(links)}</nav>'


def inject_frame_nav(
    html: str,
    view: FrameView,
    *,
    diagnostics_available: bool = False,
    admin_available: bool = False,
) -> str:
    """Insert fixed top-right controls (nav + theme toggle mount point) after ``<body>``."""
    if '<div class="frame-controls">' in html:
        return html
    controls = frame_controls_html(
        view,
        diagnostics_available=diagnostics_available,
        admin_available=admin_available,
    )
    return re.sub(r"(<body[^>]*>)", r"\1\n" + controls, html, count=1)
