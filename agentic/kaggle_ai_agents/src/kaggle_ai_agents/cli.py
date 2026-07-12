"""CLI entrypoint for local smoke runs."""

from __future__ import annotations

import sys

from kaggle_ai_agents.rendering.markdown import render_markdown
from kaggle_ai_agents.workflow import run_daily_brief


def main() -> int:
    try:
        brief = run_daily_brief(use_real_sources=True)
        print(render_markdown(brief))
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
