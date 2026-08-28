"""Migrate all reports to frame + content layout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate reports/ to frame+content layout")
    parser.add_argument("--sync-work", action="store_true")
    parser.add_argument("--no-ts-update", action="store_true")
    args = parser.parse_args()

    from rebuild_html import main as rebuild_main

    sys.argv = [
        "migrate_reports.py",
        "--all",
        *(["--sync-work"] if args.sync_work else []),
        *(["--no-ts-update"] if args.no_ts_update else []),
    ]
    rebuild_main()


if __name__ == "__main__":
    main()
