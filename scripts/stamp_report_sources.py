#!/usr/bin/env python3
"""Stamp report_source badges on digest JSON and optionally re-render HTML.

Examples:
  python scripts/stamp_report_sources.py --all --rerender --rebuild-index
  python scripts/stamp_report_sources.py --app --rerender
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from lib.paths import REPO_ROOT
from lib.report_source import (
    REPORT_SOURCE_HERMES,
    REPORT_SOURCE_LLM,
    stamp_reports_tree,
    sync_app_badge_assets,
)


def _rerender_tree(reports_dir: Path) -> int:
    from llm_pipeline.render import build_content_html

    from lib.deploy_app import list_deployable_prefixes

    _ensure_scripts_path()
    from _report_utils import leaderboards_for_prefix  # type: ignore

    count = 0
    for prefix in list_deployable_prefixes(reports_dir):
        lb = leaderboards_for_prefix(prefix, reports_dir)
        html = build_content_html(prefix, lb, reports_dir)
        (reports_dir / f"{prefix}.html").write_text(html, encoding="utf-8")
        count += 1
    return count


def _ensure_scripts_path() -> None:
    scripts = REPO_ROOT / "llm_pipeline" / "vendor" / "ai-news-digest" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))


def _rebuild_index(reports_dir: Path, *, agentic: bool = False, app: bool = False) -> None:
    if app:
        from lib.deploy_app import rebuild_app_archives

        sync_app_badge_assets()
        rebuild_app_archives()
        return
    from llm_pipeline.config import load_config
    from llm_pipeline.render import rebuild_reports_archive

    if agentic:
        import sys

        hermes = REPO_ROOT / "agentic" / "hermes"
        if str(hermes) not in sys.path:
            sys.path.insert(0, str(hermes))
        from tools.baseline import agentic_config  # type: ignore

        cfg = agentic_config()
    else:
        cfg = load_config()
    rebuild_reports_archive(cfg, reports_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stamp branch badges on digest reports")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="llm_pipeline + agentic + app")
    group.add_argument("--llm-pipeline", action="store_true")
    group.add_argument("--agentic-hermes", action="store_true")
    group.add_argument("--app", action="store_true")
    parser.add_argument("--rerender", action="store_true", help="rebuild per-prefix HTML from JSON")
    parser.add_argument("--rebuild-index", action="store_true", help="rebuild archive index.html frames")
    args = parser.parse_args()

    targets: list[tuple[Path, str | None, str, bool, bool]] = []
    if args.all or args.llm_pipeline:
        targets.append(
            (REPO_ROOT / "llm_pipeline" / "reports", REPORT_SOURCE_LLM, "llm_pipeline", False, False)
        )
    if args.all or args.agentic_hermes:
        targets.append(
            (REPO_ROOT / "agentic" / "hermes" / "reports", REPORT_SOURCE_HERMES, "agentic_hermes", True, False)
        )
    if args.all or args.app:
        targets.append((REPO_ROOT / "app" / "reports", None, "app", False, True))

    total_json = 0
    total_html = 0
    for reports_dir, source, context, agentic, app in targets:
        if not reports_dir.is_dir():
            print(f"  skip missing {reports_dir.relative_to(REPO_ROOT)}")
            continue
        print(f"== stamp {reports_dir.relative_to(REPO_ROOT)} ({context}) ==")
        n = stamp_reports_tree(reports_dir, source=source, context=context)  # type: ignore[arg-type]
        total_json += n
        print(f"  stamped {n} JSON file(s)")
        if args.rerender:
            h = _rerender_tree(reports_dir)
            total_html += h
            print(f"  re-rendered {h} HTML file(s)")
        if args.rebuild_index:
            _rebuild_index(reports_dir, agentic=agentic, app=app)
            print("  rebuilt archive index")

    print(f"\n✓ done ({total_json} JSON updated, {total_html} HTML re-rendered)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
