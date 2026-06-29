"""Stage 4: render digest JSON → HTML and rebuild the archive index frame."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pipeline.paths import SKILL_DIR, SKILL_SCRIPTS, diagnostics_dir, reports_dir
from pipeline.frame_author import inject_author_card
from pipeline.frame_nav import diagnostics_available as has_diagnostics
from pipeline.frame_nav import inject_frame_nav
from pipeline.site_footer import inject_site_footer


def _ensure_scripts_path() -> None:
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))


def build_content_html(prefix: str, leaderboards_json: str, reports_dir: Path) -> str:
    """Like _report_utils.build_content_html but writes from reports_dir JSON."""
    _ensure_scripts_path()
    from _report_utils import CONTENT_TEMPLATE, digest_app_js  # type: ignore

    template = CONTENT_TEMPLATE.read_text(encoding="utf-8")
    json_path = reports_dir / f"{prefix}.json"
    payload = json_path.read_text(encoding="utf-8").strip()
    html = (
        template.replace("__PREFIX__", prefix)
        .replace("__LEADERBOARDS__", leaderboards_json)
        .replace("__DIGEST_JSON__", payload)
        .replace("__DIGEST_APP__", digest_app_js())
    )
    return html


def render(cfg: dict[str, Any], prefix: str, data: dict[str, Any]) -> Path:
    reports = reports_dir(cfg)
    reports.mkdir(parents=True, exist_ok=True)

    json_path = reports / f"{prefix}.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  OK {json_path}")

    if not cfg.get("render", {}).get("rebuild_html", True):
        return json_path

    _ensure_scripts_path()
    from _report_utils import build_frame_html, leaderboards_for_prefix  # type: ignore
    from rebuild_index import write_index  # type: ignore

    lb = leaderboards_for_prefix(prefix, reports)
    html = build_content_html(prefix, lb, reports)
    html_path = reports / f"{prefix}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"  OK {html_path}")

    if cfg.get("render", {}).get("rebuild_index", True):
        write_index(reports_dir=reports, sync_work=False)
        frame = build_frame_html(reports_dir=reports)
        frame = inject_author_card(frame, cfg)
        frame = inject_frame_nav(
            frame,
            "reports",
            diagnostics_available=has_diagnostics(cfg, diagnostics_dir(cfg)),
        )
        frame = inject_site_footer(frame, cfg)
        (reports / "index.html").write_text(frame, encoding="utf-8")
        print(f"  OK {reports / 'index.html'}")

    return json_path
