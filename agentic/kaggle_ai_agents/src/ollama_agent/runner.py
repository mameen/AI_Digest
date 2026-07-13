"""Ollama agent runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from src.ollama_agent.agent import OllamaAgent


def main():
    """Run Ollama agent and print results."""
    model = "qwen2.5-coder:14b"
    host = "http://localhost:11434"

    print("\n" + "=" * 60)
    print("AI Digest — Ollama Agent Runner")
    print("=" * 60)

    try:
        agent = OllamaAgent(model=model, host=host, verbose=True)
    except Exception as e:
        print(f"❌ Failed to initialize agent: {str(e)[:100]}")
        return 1

    try:
        brief = agent.run()
    except Exception as e:
        print(f"❌ Agent execution failed: {str(e)[:100]}")
        return 1

    print("\n" + "=" * 60)
    print("RESULTS — Top 10 Stories (ollama_agent)")
    print("=" * 60)
    for card in brief.cards:
        print(f"  [{card.rank:2}] {card.title}")
        print(f"       {card.url}")

    # Write to JSON
    output_file = Path(__file__).parent.parent.parent / "brief_output_ollama.json"
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
