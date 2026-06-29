#!/usr/bin/env python3
"""Compare two digest JSON files (story counts, categories, significance)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = PROJECT_ROOT / "reports"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def stats(data: dict) -> dict:
    categories = data.get("categories") or []
    cat_counts = {c["id"]: len(c.get("stories") or []) for c in categories if c.get("id")}
    stories = [s for c in categories for s in c.get("stories") or []]
    return {
        "summary": (data.get("summary") or "")[:160],
        "categories": cat_counts,
        "total": len(stories),
        "sig5": sum(1 for s in stories if int(s.get("significance") or 0) == 5),
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: compare_digest.py PREFIX_A [PREFIX_B]")

    a_path = DEFAULT_DIR / f"{sys.argv[1]}.json"
    b_path = DEFAULT_DIR / f"{sys.argv[2]}.json" if len(sys.argv) > 2 else None

    if not a_path.is_file():
        raise SystemExit(f"Not found: {a_path}")

    a = stats(load(a_path))
    print(f"A {sys.argv[1]}: {a['total']} stories, sig5={a['sig5']}")
    for cid, n in sorted(a["categories"].items()):
        print(f"  {cid}: {n}")

    if b_path and b_path.is_file():
        b = stats(load(b_path))
        print(f"\nB {sys.argv[2]}: {b['total']} stories, sig5={b['sig5']}")
        for cid in sorted(set(a["categories"]) | set(b["categories"])):
            print(f"  {cid}: {a['categories'].get(cid,0)} | {b['categories'].get(cid,0)}")


if __name__ == "__main__":
    main()
