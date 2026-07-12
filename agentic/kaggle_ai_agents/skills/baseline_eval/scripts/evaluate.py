#!/usr/bin/env python3
"""Evaluate a DailyBrief against the llm_pipeline baseline in app/index.json.

Usage:
    python evaluate.py <brief_json_file> <index_json_file> [--prefix PREFIX]

Exit 0: brief is within the required threshold (gap <= 5%)
Exit 1: brief exceeds the required threshold, or input error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SKILLS_DIR = Path(__file__).parents[3]
_SRC = _SKILLS_DIR / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from kaggle_ai_agents.models import BriefCard, DailyBrief
from kaggle_ai_agents.tools.baseline_eval import evaluate_brief_against_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate brief against baseline")
    parser.add_argument("brief_file", help="Path to brief JSON file")
    parser.add_argument("index_file", help="Path to app/index.json baseline file")
    parser.add_argument("--prefix", default=None, help="Baseline prefix to compare against (default: latest)")
    args = parser.parse_args()

    for label, p in [("brief", args.brief_file), ("index", args.index_file)]:
        if not Path(p).exists():
            print(f"ERROR: {label} file not found: {p}", file=sys.stderr)
            return 1

    try:
        brief_data = json.loads(Path(args.brief_file).read_text(encoding="utf-8"))
        brief = DailyBrief.model_validate(brief_data)
    except Exception as e:
        print(f"ERROR: Could not load brief: {e}", file=sys.stderr)
        return 1

    try:
        result = evaluate_brief_against_index(
            brief=brief,
            index_path=args.index_file,
            prefix=args.prefix,
        )
    except Exception as e:
        print(f"ERROR: Evaluation failed: {e}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))

    if not result["required_pass"]:
        print(
            f"\nFAIL: worst gap {result['worst_gap_pct']}% exceeds required threshold "
            f"{result['required_threshold_pct']}%",
            file=sys.stderr,
        )
        return 1

    status = "TARGET MET" if result["target_pass"] else "REQUIRED MET"
    print(f"\n{status}: worst gap {result['worst_gap_pct']}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
