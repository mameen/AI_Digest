"""Stage 4: render digest JSON → HTML and rebuild the archive index frame."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from llm_pipeline import generator_version
from llm_pipeline.paths import SKILL_SCRIPTS, cache_dir, diagnostics_dir, reports_dir
from lib.report_source import detect_context_from_reports_dir, detect_source_from_cfg, stamp_document
from llm_pipeline.frame_author import inject_author_card, sync_author_assets
from llm_pipeline.frame_nav import diagnostics_available as has_diagnostics
from llm_pipeline.frame_nav import admin_nav_enabled, inject_frame_nav
from llm_pipeline.site_footer import inject_site_footer


def _ensure_scripts_path() -> None:
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))


def _crawl_driven_leaderboards(cfg: dict[str, Any], prefix: str, block: str) -> str:
    """Overwrite stale hand-coded rows with the run's live crawl + structured APIs."""
    from datetime import datetime

    from llm_pipeline.leaderboards import apply_crawl_leaderboards
    from llm_pipeline.structured_sources import apply_structured_leaderboards

    run_cache = cache_dir(cfg) / prefix
    try:
        updated = datetime.strptime(prefix[:8], "%Y%m%d").strftime("%b %d, %Y")
    except ValueError:
        updated = None
    block = apply_crawl_leaderboards(block, run_cache / "crawl", updated_label=updated)
    block = apply_structured_leaderboards(block, run_cache / "structured", updated_label=updated)
    return block


def build_content_html(prefix: str, leaderboards_json: str, reports: Path) -> str:
    """Like _report_utils.build_content_html but writes from reports_dir JSON."""
    _ensure_scripts_path()
    from _report_utils import (  # type: ignore
        CONTENT_TEMPLATE,
        content_styles_block,
        digest_app_js,
        theme_apply_js,
    )

    template = CONTENT_TEMPLATE.read_text(encoding="utf-8")
    json_path = reports / f"{prefix}.json"
    payload = json_path.read_text(encoding="utf-8").strip()
    html = (
        template.replace("__PREFIX__", prefix)
        .replace("__LEADERBOARDS__", leaderboards_json)
        .replace("__DIGEST_JSON__", payload)
        .replace("__DIGEST_APP__", digest_app_js())
        .replace("__STYLES__", content_styles_block())
        .replace("__THEME_JS__", theme_apply_js())
    )
    return html


def rebuild_reports_archive(cfg: dict[str, Any] | None = None, reports: Path | None = None) -> Path:
    """Write index.json + fully decorated index.html (nav, author, footer)."""
    from llm_pipeline.config import load_config

    if cfg is None:
        cfg = load_config()
    if reports is None:
        reports = reports_dir(cfg)

    _ensure_scripts_path()
    from rebuild_index import write_index  # type: ignore
    from _report_utils import build_frame_html  # type: ignore

    write_index(reports_dir=reports, sync_work=False)
    has_author_photo = sync_author_assets(reports, cfg)
    frame = build_frame_html(reports_dir=reports)
    frame = inject_author_card(
        frame,
        cfg,
        assets_prefix="../assets" if has_author_photo else None,
    )
    frame = inject_frame_nav(
        frame,
        "reports",
        diagnostics_available=has_diagnostics(cfg, diagnostics_dir(cfg)),
        admin_available=admin_nav_enabled(cfg),
    )
    frame_path = reports / "index.html"
    frame_path.write_text(inject_site_footer(frame, cfg), encoding="utf-8")
    from llm_pipeline.frame_html import assert_archive_html_ready

    assert_archive_html_ready(frame_path.read_text(encoding="utf-8"))
    print(f"  OK reports archive {frame_path}")
    return frame_path


def render(cfg: dict[str, Any], prefix: str, data: dict[str, Any]) -> Path:
    reports = reports_dir(cfg)
    reports.mkdir(parents=True, exist_ok=True)

    data["generator_version"] = generator_version(prefix)
    data = stamp_document(data, detect_source_from_cfg(cfg), detect_context_from_reports_dir(reports))
    json_path = reports / f"{prefix}.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  OK {json_path}")

    if not cfg.get("render", {}).get("rebuild_html", True):
        return json_path

    _ensure_scripts_path()
    from _report_utils import leaderboards_for_prefix  # type: ignore

    lb = leaderboards_for_prefix(prefix, reports)
    lb = _crawl_driven_leaderboards(cfg, prefix, lb)
    html = build_content_html(prefix, lb, reports)
    html_path = reports / f"{prefix}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  OK {html_path}")

    if cfg.get("render", {}).get("rebuild_index", True):
        rebuild_reports_archive(cfg, reports)

    return json_path
