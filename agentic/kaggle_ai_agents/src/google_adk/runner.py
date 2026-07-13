"""Google ADK agent runner."""

from __future__ import annotations

import json
from pathlib import Path

from src.google_adk.agent import GoogleADKAgent


def main():
    """Run Google ADK agent and print results."""
    print("\n" + "=" * 60)
    print("AI Digest — Google ADK Runner")
    print("=" * 60)

    try:
        agent = GoogleADKAgent()
    except EnvironmentError as e:
        print(f"❌ {e}")
        return 1

    brief = agent.run()

    print("\n" + "=" * 60)
    print("RESULTS — Top 10 Stories (google_adk)")
    print("=" * 60)
    for card in brief.cards:
        print(f"  [{card.rank:2}] {card.title}")
        print(f"       {card.url}")

    # Optional: write to JSON
    output_file = Path(__file__).parent.parent.parent / "brief_output_adk.json"
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
