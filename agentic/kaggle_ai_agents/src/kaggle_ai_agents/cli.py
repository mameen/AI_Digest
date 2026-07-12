"""CLI entrypoint for local smoke runs."""

from __future__ import annotations

from kaggle_ai_agents.rendering.markdown import render_markdown
from kaggle_ai_agents.workflow import run_daily_brief


def main() -> int:
    brief = run_daily_brief()
    print(render_markdown(brief))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
