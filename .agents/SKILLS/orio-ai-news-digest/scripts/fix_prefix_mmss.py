"""Fill missing seconds on 12-digit digest prefixes (YYYYMMDDHHMM -> YYYYMMDDHHMMSS)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _report_utils import REPORTS_DIR, build_frame_html, fix_missing_mmss
from rebuild_html import rebuild_one
from rebuild_index import write_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize 12-digit digest prefixes to 14-digit")
    parser.add_argument("--sync-work", action="store_true", help="Mirror reports/ to .reports/")
    parser.add_argument("--no-ts-update", action="store_true", help="Do not update generated_at")
    args = parser.parse_args()

    fixes = fix_missing_mmss()
    if not fixes:
        print("OK no 12-digit prefixes found")
        return

    for old, new in fixes:
        print(f"{old} -> {new}")
        rebuild_one(new, update_ts=not args.no_ts_update)

    write_index(sync_work=args.sync_work)
    (REPORTS_DIR / "index.html").write_text(build_frame_html(), encoding="utf-8")
    print("OK index.html")


if __name__ == "__main__":
    main()
