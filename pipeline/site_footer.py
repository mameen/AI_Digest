"""Author footer for archive HTML frames (links from config.yaml → site)."""

from __future__ import annotations

from typing import Any


def site_footer_html(cfg: dict[str, Any]) -> str:
    from pipeline import __version__
    from pipeline.frame_author import GITHUB_MARK

    site = cfg.get("site") or {}
    name = (site.get("author_short") or site.get("author_name") or "AI Digest").strip()
    linkedin = (site.get("linkedin_url") or "").strip()
    portfolio = (site.get("portfolio_url") or "").strip()
    github = (site.get("github_url") or "").strip()

    parts = [
        '<footer class="site-footer">',
        "  <span>AI Digest pipeline</span>",
        '  <span class="site-footer-sep">·</span>',
        f'  <span class="site-footer-version">v{__version__}</span>',
        '  <span class="site-footer-sep">·</span>',
        f"  <span>{name}</span>",
    ]
    if linkedin:
        parts.extend(
            [
                '  <span class="site-footer-sep">·</span>',
                f'  <a href="{linkedin}" target="_blank" rel="noopener">LinkedIn</a>',
            ]
        )
    if portfolio:
        parts.extend(
            [
                '  <span class="site-footer-sep">·</span>',
                f'  <a href="{portfolio}" target="_blank" rel="noopener">Portfolio</a>',
            ]
        )
    if github:
        parts.extend(
            [
                '  <span class="site-footer-sep">·</span>',
                f'  <a href="{github}" target="_blank" rel="noopener" '
                f'title="Source on GitHub">{GITHUB_MARK}GitHub</a>',
            ]
        )
    parts.append("</footer>")
    return "\n".join(parts)


def site_footer_css() -> str:
    return """
  .site-footer {
    flex-shrink: 0; padding: 10px 24px; font-size: 11px; color: #8b949e;
    border-top: 1px solid #30363d; background: #0d1117; text-align: center;
  }
  .site-footer a { color: #58a6ff; text-decoration: none; }
  .site-footer a:hover { text-decoration: underline; }
  .site-footer-sep { margin: 0 6px; opacity: 0.5; }
"""


def inject_site_footer(html: str, cfg: dict[str, Any]) -> str:
    """Insert footer CSS + HTML before ``</body>`` if not already present."""
    if "site-footer" in html:
        return html
    css = site_footer_css()
    footer = site_footer_html(cfg)
    if "</style>" in html and ".site-footer" not in html:
        html = html.replace("</style>", css + "\n</style>", 1)
    return html.replace("</body>", footer + "\n</body>")
