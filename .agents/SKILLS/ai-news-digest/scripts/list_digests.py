"""
List all past digests in .reports/ with their summaries and story counts.

Usage:
    python skills/ai-news-digest/scripts/list_digests.py
    python skills/ai-news-digest/scripts/list_digests.py --json
"""

import argparse
import json
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent.parent.parent / "reports"
WORK_REPORTS_DIR = Path(__file__).parent.parent.parent.parent / ".reports"
PUBLIC_BASE = ""


def load_digest(json_path: Path) -> dict:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    story_count = sum(len(c.get("stories", [])) for c in data.get("categories", []))
    prefix = json_path.stem
    return {
        "prefix": prefix,
        "generated_at": data.get("generated_at", ""),
        "summary": data.get("summary", ""),
        "story_count": story_count,
        "url": f"{PUBLIC_BASE.rstrip('/')}/{prefix}.html" if PUBLIC_BASE else f"{prefix}.html",
    }


def main():
    parser = argparse.ArgumentParser(description="List all AI digests")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON")
    args = parser.parse_args()

    paths = sorted(
        (p for p in REPORTS_DIR.glob("*.json") if len(p.stem) == 14 and p.stem.isdigit()),
        reverse=True,
    )

    if not paths:
        print(f"No digests found in {REPORTS_DIR}")
        return

    digests = [load_digest(p) for p in paths]

    if args.as_json:
        print(json.dumps(digests, indent=2, ensure_ascii=False))
        return

    print(f"{'Prefix':<16} {'Stories':>7}  {'Summary'}")
    print("-" * 80)
    for d in digests:
        summary = d.get("summary", "")
        summary_short = summary[:55] + "…" if len(summary) > 55 else summary
        print(f"{d['prefix']:<16} {d['story_count']:>7}  {summary_short}")


if __name__ == "__main__":
    main()
