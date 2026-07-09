"""
Build or refresh reports/index.json from digest JSON files.

Usage:
    python vendor/ai-news-digest/scripts/rebuild_index.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _report_utils import REPORTS_DIR, build_index


def write_index(reports_dir: Path | None = None, *, sync_work: bool = False) -> dict:
    root = reports_dir or REPORTS_DIR
    index = build_index(root)
    out = root / "index.json"
    out.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"OK {out} ({len(index['digests'])} digests, latest={index['latest']})")
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild reports/index.json")
    parser.parse_args()
    write_index()


if __name__ == "__main__":
    main()
