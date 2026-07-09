"""Author footer for archive HTML frames (links from config.yaml → site)."""

from __future__ import annotations

from typing import Any


def site_footer_html(cfg: dict[str, Any]) -> str:
    from llm_pipeline import __version__
    from llm_pipeline.frame_author import GITHUB_MARK

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
    flex-shrink: 0;
    padding: 8px 16px;
    font-size: 11px;
    line-height: 1.4;
    color: var(--muted, #8b949e);
    border-top: 1px solid var(--border, #30363d);
    background: var(--masthead-bg, #0d1117);
    text-align: center;
  }
  .site-footer a { color: var(--accent, #58a6ff); text-decoration: none; }
  .site-footer a:hover { text-decoration: underline; }
  .site-footer-sep { margin: 0 6px; opacity: 0.5; }
  .site-footer svg { vertical-align: -1px; margin-right: 2px; }
"""


def inject_site_footer(html: str, cfg: dict[str, Any], *, archive_frame: bool = True) -> str:
    """Insert footer HTML before ``</body>`` if not already present.

    Set ``archive_frame=False`` for iframe-embedded pages (no site footer).
    """
    if not archive_frame or '<footer class="site-footer">' in html:
        return html
    footer = site_footer_html(cfg)
    return html.replace("</body>", footer + "\n</body>")
