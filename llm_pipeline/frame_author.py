"""Compact author card for archive frame headers."""

from __future__ import annotations

import html
from typing import Any

_GH_PATH = "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"

GITHUB_MARK = (
    '<svg viewBox="0 0 16 16" width="10" height="10" fill="currentColor" '
    'aria-hidden="true" style="vertical-align:-1px;margin-right:2px">'
    f'<path d="{_GH_PATH}"/></svg>'
)


def author_card_css() -> str:
    return ""


def _author_photo_src(cfg: dict[str, Any], *, assets_prefix: str | None) -> str | None:
    site = cfg.get("site") or {}
    url = (site.get("author_photo_url") or "").strip()
    if url.startswith(("http://", "https://")):
        return url
    photo = (site.get("author_photo") or "ademiry.jpg").strip()
    if photo.startswith(("http://", "https://")):
        return photo
    if assets_prefix:
        return f"{assets_prefix}/{photo}"
    return None


def author_card_html(cfg: dict[str, Any], *, assets_prefix: str | None = "../assets") -> str:
    site = cfg.get("site") or {}
    name = (site.get("author_name") or "Ameen Demiry").strip()
    bio = (
        site.get("author_bio")
        or "Senior engineer with extensive experience in developing distributed and cloud-based solutions."
    ).strip()
    photo_src = _author_photo_src(cfg, assets_prefix=assets_prefix)
    linkedin = (site.get("linkedin_url") or "").strip()
    portfolio = (site.get("portfolio_url") or "").strip()
    github = (site.get("github_url") or "").strip()

    links: list[str] = []
    if linkedin:
        links.append(
            f'<a href="{html.escape(linkedin)}" target="_blank" rel="noopener">LinkedIn</a>'
        )
    if portfolio:
        links.append(
            f'<a href="{html.escape(portfolio)}" target="_blank" rel="noopener">Portfolio</a>'
        )
    if github:
        links.append(
            f'<a href="{html.escape(github)}" target="_blank" rel="noopener" title="Source on GitHub">'
            f'{GITHUB_MARK}GitHub</a>'
        )
    link_row = " · ".join(links)

    photo_html = (
        f'<img src="{html.escape(photo_src)}" alt="{html.escape(name)}" '
        f'width="32" height="32" loading="lazy">'
        if photo_src
        else ""
    )
    return f"""<div class="frame-author" role="complementary" aria-label="Author" onclick="event.stopPropagation()">
  <button type="button" class="frame-author-dismiss" aria-label="Collapse profile card">&times;</button>
  <div class="frame-author-body">
    <div class="frame-author-main">
      {photo_html}
      <div class="frame-author-text">
        <span class="frame-author-name">{html.escape(name)}</span>
        <span class="frame-author-bio">{html.escape(bio)}</span>
        {f'<span class="frame-author-links">{link_row}</span>' if link_row else ''}
      </div>
    </div>
  </div>
</div>"""


def sync_author_assets(
    reports_dir: Path,
    cfg: dict[str, Any],
    *,
    repo: Path | None = None,
) -> bool:
    """Copy the configured author headshot beside *reports_dir* (``../assets/`` in frames)."""
    import shutil

    from lib.paths import REPO_ROOT

    site = cfg.get("site") or {}
    if (site.get("author_photo_url") or "").strip().startswith(("http://", "https://")):
        return False
    photo = (site.get("author_photo") or "ademiry.jpg").strip()
    if photo.startswith(("http://", "https://")):
        return False
    src = (repo or REPO_ROOT) / "llm_pipeline" / "assets" / photo
    if not src.is_file():
        return False
    dest = reports_dir.parent / "assets"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest / photo)
    return True


def inject_author_card(
    html: str,
    cfg: dict[str, Any],
    *,
    assets_prefix: str | None = "../assets",
) -> str:
    """Insert author card markup and replace ``__AUTHOR_CARD__`` placeholder."""
    card = author_card_html(cfg, assets_prefix=assets_prefix)
    if "__AUTHOR_CARD__" in html:
        return html.replace("__AUTHOR_CARD__", card)
    marker = "</div>\n</details>"
    if marker in html and "frame-author" not in html:
        return html.replace(marker, card + "\n  " + marker, 1)
    return html
