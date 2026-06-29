"""Compact author card for archive frame headers."""

from __future__ import annotations

import html
from typing import Any

_GH_PATH = "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"

GITHUB_MARK = (
    '<svg viewBox="0 0 16 16" width="11" height="11" fill="currentColor" '
    'aria-hidden="true" style="vertical-align:-1px;margin-right:2px">'
    f'<path d="{_GH_PATH}"/></svg>'
)


def author_card_css() -> str:
    return """
  .heatmap-body, .archive-body { position: relative; padding-bottom: 4px; }
  @media (min-width: 901px) {
    .heatmap-body, .archive-body { padding-right: 410px; min-height: 108px; }
  }
  .frame-author {
    position: absolute; bottom: 14px; right: 20px; z-index: 40;
    display: flex; flex-direction: column; gap: 8px;
    max-width: min(390px, calc(100% - 40px));
    padding: 8px 12px; border: 1px solid var(--border, #30363d);
    border-radius: 8px; background: var(--card-bg, #161b22);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  }
  .frame-author-main { display: flex; align-items: center; gap: 10px; }
  .frame-author img {
    width: 40px; height: 40px; border-radius: 50%;
    object-fit: cover; flex-shrink: 0;
  }
  .frame-author-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
  .frame-author-name { font-size: 11px; font-weight: 600; color: var(--text, #e6edf3); }
  .frame-author-bio {
    font-size: 10px; color: var(--muted, #8b949e); line-height: 1.35;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }
  .frame-author-links { font-size: 10px; margin-top: 1px; }
  .frame-author-links a { color: var(--accent, #58a6ff); text-decoration: none; }
  .frame-author-links a:hover { text-decoration: underline; }
  .frame-author-oss {
    font-size: 10px; color: var(--muted, #8b949e); line-height: 1.4;
  }
  .frame-author-oss a { color: var(--accent, #58a6ff); text-decoration: none; white-space: nowrap; }
  .frame-author-oss a:hover { text-decoration: underline; }
  .frame-author-divider {
    height: 1px; width: 100%; flex-shrink: 0;
    background: var(--border, #30363d);
  }
  @media (max-width: 900px) {
    .frame-author { display: none; }
  }
"""


def author_card_html(cfg: dict[str, Any], *, assets_prefix: str = "../assets") -> str:
    site = cfg.get("site") or {}
    name = (site.get("author_name") or "Ameen Demiry").strip()
    bio = (
        site.get("author_bio")
        or "Senior engineer with extensive experience in developing distributed and cloud-based solutions."
    ).strip()
    photo = (site.get("author_photo") or "ademiry.jpg").strip()
    linkedin = (site.get("linkedin_url") or "").strip()
    portfolio = (site.get("portfolio_url") or "").strip()
    github = (site.get("github_url") or "").strip()

    oss = ""
    if github:
        oss = (
            '<div class="frame-author-oss">This pipeline is open source and '
            f'available on <a href="{html.escape(github)}" target="_blank" '
            f'rel="noopener">{GITHUB_MARK}GitHub</a>.</div>'
            '\n  <div class="frame-author-divider"></div>\n  '
        )

    links: list[str] = []
    if linkedin:
        links.append(
            f'<a href="{html.escape(linkedin)}" target="_blank" rel="noopener">LinkedIn</a>'
        )
    if portfolio:
        links.append(
            f'<a href="{html.escape(portfolio)}" target="_blank" rel="noopener">Portfolio</a>'
        )
    link_row = " · ".join(links)

    return f"""<div class="frame-author" onclick="event.stopPropagation()">
  {oss}<div class="frame-author-main">
    <img src="{html.escape(assets_prefix)}/{html.escape(photo)}" alt="{html.escape(name)}" width="40" height="40" loading="lazy">
    <div class="frame-author-text">
      <span class="frame-author-name">{html.escape(name)}</span>
      <span class="frame-author-bio">{html.escape(bio)}</span>
      {f'<span class="frame-author-links">{link_row}</span>' if link_row else ''}
    </div>
  </div>
</div>"""


def inject_author_card(html: str, cfg: dict[str, Any]) -> str:
    """Insert author card CSS and replace ``__AUTHOR_CARD__`` placeholder."""
    card = author_card_html(cfg)
    if ".frame-author" not in html and "</style>" in html:
        html = html.replace("</style>", author_card_css() + "\n</style>", 1)
    if "__AUTHOR_CARD__" in html:
        return html.replace("__AUTHOR_CARD__", card)
    marker = "</div>\n</details>"
    if marker in html and "frame-author" not in html:
        return html.replace(marker, card + "\n  " + marker, 1)
    return html
