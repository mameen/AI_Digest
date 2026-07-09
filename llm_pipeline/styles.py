"""Load shared CSS bundles for digest, archive frame, and diagnostics pages."""

from __future__ import annotations

from llm_pipeline.paths import SKILL_DIR

STYLES_DIR = SKILL_DIR / "styles"
THEME_JS = SKILL_DIR / "theme.js"
THEME_APPLY_JS = SKILL_DIR / "theme-apply.js"
TREND_CHARTS_JS = SKILL_DIR / "trend-charts.js"
HEATMAP_JS = SKILL_DIR / "heatmap.js"


def _read(name: str) -> str:
    return (STYLES_DIR / name).read_text(encoding="utf-8")


def bundle_styles(*names: str) -> str:
    return "\n".join(_read(n) for n in names)


def theme_script() -> str:
    return THEME_JS.read_text(encoding="utf-8")


def theme_apply_script() -> str:
    return THEME_APPLY_JS.read_text(encoding="utf-8")


def trend_charts_script() -> str:
    return TREND_CHARTS_JS.read_text(encoding="utf-8")


def heatmap_script() -> str:
    return HEATMAP_JS.read_text(encoding="utf-8")


def digest_styles() -> str:
    return bundle_styles("dark.css", "light.css")


def frame_styles() -> str:
    return bundle_styles("dark.css", "light.css", "frame.css")


def diagnostics_waterfall_styles() -> str:
    return bundle_styles("dark.css", "light.css", "diagnostics.css")
