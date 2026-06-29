"""Compact author card for archive frame headers."""

from __future__ import annotations

import html
from typing import Any


def author_card_css() -> str:
    return """
  .heatmap-body, .archive-body { position: relative; padding-bottom: 4px; }
  @media (min-width: 901px) {
    .heatmap-body, .archive-body { padding-right: 400px; min-height: 88px; }
  }
  .frame-author {
    position: absolute; bottom: 14px; right: 20px; z-index: 40;
    display: flex; align-items: center; gap: 10px;
    max-width: min(380px, calc(100% - 40px));
    padding: 8px 12px; border: 1px solid var(--border, #30363d);
    border-radius: 8px; background: var(--card-bg, #161b22);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  }
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
  <img src="{html.escape(assets_prefix)}/{html.escape(photo)}" alt="{html.escape(name)}" width="40" height="40" loading="lazy">
  <div class="frame-author-text">
    <span class="frame-author-name">{html.escape(name)}</span>
    <span class="frame-author-bio">{html.escape(bio)}</span>
    {f'<span class="frame-author-links">{link_row}</span>' if link_row else ''}
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
