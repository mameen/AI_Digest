---
name: source-normalization
description: Normalize heterogeneous source records from RSS, web, and YouTube into the unified NewsItem schema. Use when raw fetched records have inconsistent field names and need to be standardized before deduplication or ranking.
metadata:
  author: kaggle-ai-agents
  version: "1.0"
---

# Source Normalization Skill

Maps raw source records with varying field names into a single consistent schema.

## When to use

- After fetching records from RSS feeds, web scrapes, or YouTube channels
- Before passing items to `dedupe_and_rank`
- When source records use different field names for the same concept

## Field mapping rules

Input records may use any of these field names:

| Canonical field | Accepted input names |
|---|---|
| `title` | `title`, `headline` |
| `url` | `url`, `source_url` |
| `summary` | `summary`, `raw_excerpt` |
| `source_id` | `source_id` (required; falls back to `"unknown"`) |

## Instructions

1. Receive a list of raw source records (dicts with varying field names).
2. For each record, apply the field mapping above to extract `title`, `url`, `summary`, and `source_id`.
3. If `title` is missing after mapping, skip the record and log it.
4. If `url` is missing, use `https://example.com` as a fallback (log it as low-quality).
5. Pass all successfully normalized records to the `dedupe_and_rank` skill.

## Code reference

`src/kaggle_ai_agents/tools/news_sources.py` — `normalize_source_records()`
