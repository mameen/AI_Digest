"""
Copy frame.html to reports/index.html and refresh index.json.

Usage:
    python skills/ai-news-digest/scripts/rebuild_frame.py
    python skills/ai-news-digest/scripts/rebuild_frame.py --sync-work
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _report_utils import REPORTS_DIR, build_frame_html, sync_work_reports
from rebuild_index import write_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild reports/index.html")
    parser.add_argument("--sync-work", action="store_true", help="Mirror reports/ to .reports/")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    write_index(sync_work=args.sync_work)
    target = REPORTS_DIR / "index.html"
    target.write_text(build_frame_html(), encoding="utf-8")
    print(f"OK {target}")


if __name__ == "__main__":
    main()
