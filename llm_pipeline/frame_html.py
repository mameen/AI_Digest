"""Shared validation for archive frame HTML builds."""

from __future__ import annotations

FRAME_PLACEHOLDERS = (
    "__AUTHOR_CARD__",
    "__FRAME_STYLES__",
    "__CONTENT_STYLES__",
    "__THEME_JS__",
    "__HEATMAP_JS__",
    "__TREND_CHARTS_JS__",
    "__CONTENT_PANEL__",
    "__INDEX_SCRIPT__",
    "__DIGESTS_SCRIPT__",
    "__LEADERBOARDS__",
    "__DIGEST_APP__",
)


def assert_archive_html_ready(html: str) -> None:
    """Fail fast if template placeholders leaked into built HTML."""
    leaked = [token for token in FRAME_PLACEHOLDERS if token in html]
    if leaked:
        raise RuntimeError(
            "Archive HTML still contains unreplaced placeholders: " + ", ".join(leaked)
        )
