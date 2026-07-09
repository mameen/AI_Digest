#!/usr/bin/env python3
"""Deploy digest reports from pipeline or agentic Hermes into ``app/``.

Examples:
  # Preview new agentic reports not yet in app/
  python scripts/deploy_app.py --agentic-hermes --auto

  # Deploy one run (your example)
  python scripts/deploy_app.py --not-dry-run --agentic-hermes --one-day 20260707182407

  # Deploy new pipeline reports
  python scripts/deploy_app.py --pipeline --auto --not-dry-run

  # Bootstrap / resync all pipeline reports into app/
  python scripts/deploy_app.py --pipeline --all --not-dry-run

Output layout (report artifacts only — no shared assets; branches stay unaware of app/):
  app/reports/       per-run HTML + JSON
  app/diagnostics/   matching diagnostics artifacts (when present)
  app/index/         archive frame (index.html + index.json)
  app/index.json     digest manifest (same data; updated on every deploy)
  app/index.html     redirect to app/index/index.html
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from lib.deploy_app import (  # noqa: E402
    app_root,
    execute_deploy,
    plan_deploy,
    rebuild_app_archives,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy digest artifacts into ./app/")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--pipeline", action="store_true", help="source: llm_pipeline/reports")
    src.add_argument(
        "--agentic-hermes",
        action="store_true",
        help="source: agentic/hermes/reports",
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--auto",
        action="store_true",
        help="deploy prefixes present in source but not yet in app/reports/",
    )
    mode.add_argument(
        "--all",
        action="store_true",
        help="deploy every prefix in source (initial bootstrap / full resync)",
    )
    mode.add_argument(
        "--one-day",
        metavar="PREFIX",
        help="deploy one run prefix (e.g. 20260707182407)",
    )

    dry = parser.add_mutually_exclusive_group()
    dry.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="preview only (default)",
    )
    dry.add_argument(
        "--not-dry-run",
        action="store_true",
        help="copy files and rebuild app/index archives",
    )

    args = parser.parse_args()
    source_kind = "agentic-hermes" if args.agentic_hermes else "pipeline"
    deploy_mode = "auto" if args.auto else ("all" if args.all else "one-day")
    dry_run = not args.not_dry_run

    try:
        plan = plan_deploy(
            source_kind=source_kind,
            mode=deploy_mode,
            prefix=args.one_day,
            dry_run=dry_run,
        )
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR {exc}")
        return 1

    app = app_root()
    print(f"== deploy-app: {'dry-run' if dry_run else 'apply'} ==")
    print(f"  source: {plan.source.label}")
    print(f"  dest:   {app.relative_to(REPO)}/")
    if not plan.prefixes:
        print("  nothing to deploy (auto: all source prefixes already in app/reports/)")
        return 0

    print(f"  prefixes ({len(plan.prefixes)}): {', '.join(plan.prefixes)}")
    for src, dest in plan.copies:
        print(f"  {'would copy' if dry_run else 'copy'} {src.relative_to(REPO)} → {dest.relative_to(REPO)}")

    manifest = execute_deploy(plan)
    if dry_run:
        print("\n  (dry-run — pass --not-dry-run to apply)")
    else:
        rebuild_note = "rebuilt app/index/ + app/diagnostics/index (if any)"
        print(f"\n  ✓ deployed {len(plan.prefixes)} prefix(es); {rebuild_note}")
        print(f"  manifest: {app / 'deploy_manifest.json'}")
        print(f"  open: file://{(app / 'index' / 'index.html').resolve()}")

    if args.not_dry_run and len(manifest.get("files", [])) > 0:
        pass  # manifest written by execute_deploy
    elif dry_run and manifest.get("files"):
        print(f"\n  files: {len(manifest['files'])}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
