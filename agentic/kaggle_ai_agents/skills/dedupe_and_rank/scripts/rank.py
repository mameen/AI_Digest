#!/usr/bin/env python3
"""Deduplicate and rank news items from a JSON file.

Usage:
    python rank.py <items_json_file> [--limit N]

Input JSON: list of {source_id, title, url, summary} objects
Output: ranked JSON array printed to stdout
Exit 0: success
Exit 1: input error or validation failure
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from any working directory by adding src/ to path
_SKILLS_DIR = Path(__file__).parents[3]
_SRC = _SKILLS_DIR / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from kaggle_ai_agents.models import NewsItem
from kaggle_ai_agents.tools.selection import rank_items


def main() -> int:
    parser = argparse.ArgumentParser(description="Deduplicate and rank news items")
    parser.add_argument("items_file", help="Path to JSON file containing list of news items")
    parser.add_argument("--limit", type=int, default=5, help="Maximum items to return (default 5)")
    args = parser.parse_args()

    path = Path(args.items_file)
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        return 1

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        return 1

    if not isinstance(raw, list):
        print("ERROR: Input must be a JSON array", file=sys.stderr)
        return 1

    try:
        items = [NewsItem.model_validate(r) for r in raw]
    except Exception as e:
        print(f"ERROR: Item validation failed: {e}", file=sys.stderr)
        return 1

    ranked = rank_items(items, limit=args.limit)
    output = [
        {"rank": i + 1, "source_id": item.source_id, "title": item.title,
         "url": str(item.url), "summary": item.summary}
        for i, item in enumerate(ranked)
    ]
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
