# ADR-003: Shared ingestion in `lib/ingest`

**Status:** Accepted  
**Date:** 2026-07-06  
**Scope:** Where YouTube, crawl, API, and web-search logic lives  

**Related:** [002](002-repo-layout-and-pipeline-deprecation.md), [004](004-extractors-vs-topics.md), [../ARCHITECTURE.md](../ARCHITECTURE.md)

---

## Context

Digest inputs span several **source kinds** (YouTube/RSS, crawl markdown,
structured JSON, preflight skeleton). Hermes researchers and `llm_pipeline` must
share the same stage-1 data without duplicating fetch logic or exposing a
Hermes tool per topic (`fetch_robotics`, `crawl_leaderboard`, …).

---

## Decision

### 1. Implement once under `lib/ingest/`

```
lib/ingest/
├── stage1.py           # run_preflight, crawl_leaderboards, fetch_structured_sources
├── bundle.py           # warm_bundle() — once per run prefix
├── compose.py          # registry binding → generic extractors
├── extractors/         # rss, preflight, crawl, structured
├── topics/registry.py  # topic id → source kinds (data only)
├── dispatch.py         # compose helpers + test seed_topic_workspace
├── agent_tools.py      # JSON helpers for digest-tools plugin
└── markdown.py         # bullets → output.md
```

**Dependency rule:** `llm_pipeline/run.py` imports `lib.ingest.stage1` directly.
`llm_pipeline/fetch.py` is a shim for `pipeline/` compatibility only.

### 2. Thin wrappers per track

| Track | Entry | Role |
|-------|---------|------|
| `llm_pipeline/` | `run.py` → `lib.ingest.stage1` | Full staged pipeline |
| `agentic/hermes/` | `manage.py go` → `warm_bundle` + worker dispatch | Agentic digest |
| Hermes workers | `plugins/digest-tools` | Generic ingest tools |
| `tools/baseline.py` | validate/render/enrich only | No ingest wrappers |

### 3. Hermes agent tools (generic, not per-topic)

| Tool | Purpose |
|------|---------|
| `verify_url` | Liveness + soft-404 check |
| `fetch_rss` | Syndication fetch |
| `read_preflight_category` | Stage1 skeleton category |
| Hermes `web_search` (ddgs) | Discover URLs — configured by `setup` |

Workers **plan** with these tools; LLM composes `output.md`. No `research_topic`
on the digest toolset (library/test helper only).

### 4. Adding a digest topic

1. Add row to `lib/ingest/topics/registry.py` (`TopicBinding`)
2. Add topic to `hermes_roles.yaml` `demo_topics`
3. No new Hermes plugin unless the **handoff contract** changes

---

## Consequences

- **Positive:** One stage-1 path; generic extractors; single worker pipeline
- **Negative:** `stage1.py` still uses `llm_pipeline.paths` for cache layout
- **Done:** Stable handover seeding removed; `go` dispatches real workers
