---
name: dedupe-and-rank
description: Deduplicate a list of news items by title and host, then rank by relevance score. Use when asked to remove duplicates from fetched items or produce a ranked shortlist.
compatibility: Requires python3 and kaggle_ai_agents package on PYTHONPATH
metadata:
  author: kaggle-ai-agents
  version: "1.0"
---

# Dedupe and Rank Skill

Removes duplicate stories and ranks survivors by relevance score.

## When to use

- After fetching items from multiple sources that may overlap
- Before passing items to the brief synthesis step
- When the user asks for a shortlist of the most relevant stories

## Instructions

1. Collect the full list of fetched `NewsItem` records as a JSON array.
2. Write them to a temporary file or pass the file path to the script.
3. Run the rank script:
   ```
   python skills/dedupe_and_rank/scripts/rank.py <items_json_file> [--limit N]
   ```
4. The script prints a ranked JSON array to stdout.
5. If exit code is 0, use the output as the ranked item list for the next step.
6. If exit code is 1, report the error and stop.

## Deduplication rule

Two items are duplicates when they share the same normalised title AND the same URL host. The first occurrence is kept; later ones are dropped.

## Scoring

Items are scored on three signals (higher = more relevant):

- +3 if title or summary contains "benchmark"
- +2 if title or summary contains "standard" or "interoperability"
- +1 if a non-empty summary is present

Items with equal scores are sorted alphabetically by title.
