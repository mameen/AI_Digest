"""Fully scripted agent runner."""

from __future__ import annotations

import json
from pathlib import Path

from src.fully_scripted.agent import FullyScriptedAgent


def main():
    """Run fully scripted agent and print results."""
    print("\n" + "=" * 60)
    print("AI Digest — Fully Scripted Runner")
    print("=" * 60)

    agent = FullyScriptedAgent()
    brief = agent.run()

    print("\n" + "=" * 60)
    print("RESULTS — Top 10 Stories (fully_scripted)")
    print("=" * 60)
    for card in brief.cards:
        print(f"  [{card.rank:2}] {card.title}")
        print(f"       {card.url}")

    # Optional: write to JSON
    output_file = Path(__file__).parent.parent.parent / "brief_output.json"
    out_dict = {
        "date": brief.date,
        "theme": brief.theme,
        "schema_version": brief.schema_version,
        "cards": [
            {
                "rank": c.rank,
                "title": c.title,
                "url": c.url,
                "why_it_matters": c.why_it_matters,
            }
            for c in brief.cards
        ],
    }
    with open(output_file, "w") as f:
        json.dump(out_dict, f, indent=2)
    print(f"\n✅ Written to {output_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
