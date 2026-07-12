---
name: source-discovery
description: Fetch news items from configured sources (RSS, YouTube, web scrape, APIs) and apply security filtering. Use when starting the daily brief workflow to gather items from the source registry.
compatibility: Requires python3, requests/urllib, and kaggle_ai_agents package on PYTHONPATH
metadata:
  author: kaggle-ai-agents
  version: "1.0"
---

# Source Discovery Skill

Fetches news items from a configured source registry and applies security gate filtering to block injection attacks.

## When to use

- At the start of the daily brief workflow to fetch fresh items
- When the user asks to "gather news from all sources"
- After adding a new source to the project config

## Instructions

1. Ensure the source registry is configured in `config/project.yaml` with sources of kind: `rss`, `youtube_rss`, `youtube_channel`, `web_scrape`, `js_crawl`, `structured_json`, or `mixed`.

2. Run the discovery script:
   ```
   python skills/source_discovery/scripts/discover.py --config config/project.yaml
   ```

3. To fetch from specific sources only, pass `--sources`:
   ```
   python skills/source_discovery/scripts/discover.py --config config/project.yaml --sources openai-blog deepmind-blog
   ```

4. The script outputs a JSON array of `NewsItem` objects to stdout:
   ```json
   [
     {
       "source_id": "openai-blog",
       "title": "Model Name Announced",
       "url": "https://openai.com/blog/...",
       "summary": "Summary text..."
     }
   ]
   ```

5. If exit code is 0, use the output for the next step (dedupe-and-rank).
6. If exit code is 1, check stderr for the error and stop.

## Sources and adapters

| Kind | Adapter | Status |
|---|---|---|
| `rss` | urllib + xml.etree parsing | ✅ Implemented |
| `youtube_rss` | urllib + xml.etree parsing | ✅ Implemented |
| `youtube_channel` | (stub) | 🔄 TODO |
| `web_scrape` | (stub) | 🔄 TODO |
| `js_crawl` | (stub) | 🔄 TODO |
| `structured_json` | (stub) | 🔄 TODO |
| `mixed` | (stub) | 🔄 TODO |

## Security

The security gate applies two layers of filtering:

1. **URL validation** — Pydantic `HttpUrl` model rejects schemes like `javascript:`, `data:`, etc. at parse time.
2. **Content filtering** — deny-list checks block common injection patterns:
   - HTML injection: `<script>`, `<iframe>`, `<object>`, `<embed>`, `<form>`
   - Prompt injection: "ignore instructions", "new instructions", "disregard rules", etc.

Blocked items are silently dropped; only clean items appear in the output.

## Config schema

Sources are defined in `config/project.yaml`:

```yaml
sources:
  - id: openai-blog
    kind: rss
    label: OpenAI Blog
    url: https://openai.com/blog/feed.rss
    notes: |
      Latest announcements and research updates from OpenAI
```

Add new sources to this file to include them in discovery.
