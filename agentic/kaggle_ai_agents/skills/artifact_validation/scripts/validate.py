#!/usr/bin/env python3
"""Validate a DailyBrief JSON artifact against the required schema.

Usage:
    python validate.py <brief_json_file>

Exit 0: brief is valid
Exit 1: validation failed (errors printed to stderr)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SKILLS_DIR = Path(__file__).parents[3]
_SRC = _SKILLS_DIR / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pydantic import ValidationError
from kaggle_ai_agents.validation.schemas import validate_brief


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate.py <brief_json_file>", file=sys.stderr)
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"ERROR: File not found: {path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        return 1

    try:
        brief = validate_brief(data)
    except ValidationError as e:
        print(f"VALIDATION FAILED:\n{e}", file=sys.stderr)
        return 1

    print(f"VALID: {len(brief.cards)} cards, date={brief.date}, theme={brief.theme!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
