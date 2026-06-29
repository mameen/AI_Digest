"""Top-right cross-link between digest archive and diagnostics (relative paths)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

FrameView = Literal["reports", "diagnostics"]

REPORTS_INDEX = "../reports/index.html"
DIAGNOSTICS_INDEX = "../diagnostics/index.html"


def diagnostics_available(cfg: dict[str, Any] | None = None, diag_dir: Path | None = None) -> bool:
    if diag_dir is not None:
        return any(diag_dir.glob("*.diagnostics.json"))
    if cfg is None:
        from pipeline.config import load_config

        cfg = load_config()
    from pipeline.paths import diagnostics_dir

    return any(diagnostics_dir(cfg).glob("*.diagnostics.json"))


def frame_nav_css() -> str:
    return """
  .frame-nav {
    position: fixed; top: 10px; right: 14px; z-index: 300;
    display: flex; gap: 8px;
  }
  .frame-nav a {
    display: flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; border-radius: 8px;
    border: 1px solid var(--border, #30363d);
    background: var(--card-bg, #161b22);
    text-decoration: none; font-size: 17px; line-height: 1;
    opacity: 0.88; transition: opacity 0.15s, border-color 0.15s;
  }
  .frame-nav a:hover { opacity: 1; border-color: var(--accent, #58a6ff); }
  .frame-nav a[aria-current="page"] {
    border-color: var(--accent, #58a6ff);
    box-shadow: 0 0 0 1px #388bfd44;
    cursor: default; pointer-events: none;
  }
"""


def frame_nav_html(view: FrameView, *, diagnostics_available: bool = False) -> str:
    """Reports: gear link to diagnostics when data exists. Diagnostics: newspaper back to reports."""
    if view == "reports":
        if not diagnostics_available:
            return ""
        return (
            '<nav class="frame-nav" aria-label="Switch view">'
            f'<a href="{DIAGNOSTICS_INDEX}" title="Pipeline diagnostics">⚙️</a>'
            "</nav>"
        )
    return (
        '<nav class="frame-nav" aria-label="Switch view">'
        f'<a href="{REPORTS_INDEX}" title="Digest archive">📰</a>'
        "</nav>"
    )


def inject_frame_nav(
    html: str,
    view: FrameView,
    *,
    diagnostics_available: bool = False,
) -> str:
    """Insert nav CSS + top-right link after ``<body>``."""
    nav = frame_nav_html(view, diagnostics_available=diagnostics_available)
    if not nav:
        return html
    if "frame-nav" not in html and "</style>" in html and ".frame-nav" not in html:
        html = html.replace("</style>", frame_nav_css() + "\n</style>", 1)
    marker = '<nav class="frame-nav"'
    if marker not in html:
        html = html.replace("<body>", "<body>\n" + nav, 1)
    return html
