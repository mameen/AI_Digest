# Tuning guide — content, attention, and sources

This document maps **every knob that shapes what the digest says, how much of it you get, and where links come from**. Start here when you want to change editorial voice, category depth, YouTube coverage, or LLM behavior.

Related: [`pipeline/editorial_brief.md`](../pipeline/editorial_brief.md) (injected into **every** enrich prompt), [`config.yaml`](../config.yaml) (runtime targets), [`.agents/onboarding/architecture.md`](../.agents/onboarding/architecture.md) (pipeline stages).

---

## Pipeline stages (what runs when)

| Stage | Script / module | What it controls |
|-------|-----------------|------------------|
| **Ingest / preflight** | `vendor/ai-news-digest/scripts/preflight.py` | Raw feeds: theAIsearch chapters, YouTube channels, typography, research, robotics, llm-stats |
| **YouTube wide net** | `vendor/ai-news-digest/scripts/youtube_channels.py` | Which channels, topic extraction, **tool/repo `links[]` parsing** |
| **theAIsearch** | `vendor/ai-news-digest/scripts/fetch_video_chapters.py` | Latest video chapters + description + `links[]` |
| **Enrich** | `pipeline/enrich.py` | **All LLM prompts** — summaries, scores, gap fill, curation |
| **Grounding guard** | `pipeline/grounding.py` | Demotes invented URLs on gap categories (keeps topic, clears bad link) |
| **Validate** | `pipeline/validate.py` | Min story counts, required categories |
| **Render** | `pipeline/render.py` + `vendor/ai-news-digest/digest-app.js` | HTML archive + card UI |

Run a single day:

```bash
python run.py --start 2026-07-03 --history 10
```

Preflight only (refresh feeds):

```bash
python vendor/ai-news-digest/scripts/preflight.py --prefix 20260703120000 --force
```

---

## LLM enrich prompts (review these)

All enrich calls prepend the full **editorial brief** (`pipeline/editorial_brief.md`), then add a task-specific block from `pipeline/enrich.py`.

### Pass 1 — Skeleton categories (`aisearch`, `youtube`, `research`, `typography`, `robotics`)

**Function:** `_llm_category_enrich()`  
**Template:**

```
{editorial_brief}

## Task
Enrich category **{label}** (`{id}`), {batch}.
Editorial window: {from} through {to}.

## Input stories (keep ids and urls exactly)
{stories JSON}

## Extra rules          ← category-specific (_skeleton_rules)
## Ingestion context    ← YouTube descriptions / aisearch description / crawl text
## Prior digests

Return JSON with enriched stories only.
```

**Category extra rules** (`_skeleton_rules` in `enrich.py`):

| Category | Key instruction |
|----------|-----------------|
| `aisearch` | Same story count; keep ids/urls; name tools/repos in summary; **`links[]` preserved at ingest** |
| `youtube` | Same story count; keep channel metadata; name primary tool/repo per chapter; **`links[]` preserved at ingest** |
| `research` | Score for practitioner significance |
| `typography` | Text rendering / fonts / design workflow |
| `robotics` | Humanoid / embodied / deployments |

**Ingestion context for YouTube:** `format_youtube_ingestion_block()` — full channel video descriptions (tools, chapters, links).

**After LLM:** `_merge_skeleton_fields(..., "links")` copies parsed **`links[]`** back onto stories (LLM cannot drop GitHub URLs).

### Pass 1b — Curation (`_llm_curate_category`)

Runs when `enrich.category_targets.{cat}` is a number and skeleton exceeds it.

| Category | Default target |
|----------|----------------|
| `aisearch` | **10** (from ~13 chapters) |
| `youtube` | **`null`** (keep all topics) |
| `research` | 6 |
| `typography` | 4 |
| `robotics` | 5 |

Edit targets in **`config.yaml`** → `enrich.category_targets`.

### Pass 2 — Leaderboard (`_llm_leaderboard`)

6 stories from crawled leaderboard markdown + llm-stats.

### Pass 3 — Gap fill (`_llm_gap_fill`)

Authors `analytics`, `agentic-ai`, `llm`, `rag`, `image-gen`, `design-ai` from ingestion context. **Strict URL grounding** — must cite URLs seen in crawl text.

### Pass 4 — Daily summary (`_llm_summary`)

One-sentence masthead + aisearch video label.

### Optional — Tool loop (`enrich.tool_loop.enabled`)

Agentic URL verification for gap stories (default **off**). See `_tool_loop_system` in `enrich.py`.

---

## Editorial voice & prose

**File:** `pipeline/editorial_brief.md`

| Section | Effect |
|---------|--------|
| Prose style | No em dashes, no filler ("landscape", "delve"), prefer concrete facts |
| Cast the net wide | Category list and default story counts |
| aisearch / youtube rules | Special-case behavior vs other categories |
| Story fields | Summary length, scores 1–5, tags |
| Prior digests | De-duplication guidance |

Changes here affect **every** enrich call immediately on the next run.

---

## Sources & attention

### YouTube secondary channels

**File:** `vendor/ai-news-digest/scripts/youtube_channels.py`

```python
SECONDARY_CHANNELS = [
    {"key": "ibm-technology", "label": "IBM Technology", ...},
    {"key": "google-cloud-tech", ...},
    {"key": "the-stack-ai", "label": "The Stack", ...},
    ...
]
```

- Add/remove channels in this list.
- Topic extraction: yt-dlp chapters → description timestamps → whole video.
- **`link_extract.py`** — shared parser: GitHub, X, LinkedIn, Hugging Face, arXiv, announcement URLs
- **Named product URLs** (`OpenCode: https://opencode.ai`) are kept from tools blocks and `name: url` description lines; bare domains without a label are still skipped
- **`parse_description_resources()`** — YouTube “Tools & resources” block
- **`match_resources_to_topics()`** — chapter-primary ordering; tune **`_TOPIC_RESOURCE_HINTS`** in `youtube_channels.py`
- **`attach_story_embedded_links()`** — scans title, summary, raw_snippet, RSS/HTML body fields on **every** story (all categories)
- **`_reattach_skeleton_links()`** in `enrich.py` — re-applies links for **all skeleton categories** (works with cached preflight)
- **`_finalize_story_links()`** — re-scans embedded text after LLM enrich (gap, leaderboard, summaries with URLs)

### theAIsearch (always separate category)

**File:** `vendor/ai-news-digest/scripts/fetch_video_chapters.py`  
Never goes into `youtube`. Curated to 10 after enrich by default.

### Category targets & validation

**File:** `config.yaml`

```yaml
enrich:
  stories_per_batch: 18
  category_targets:
    aisearch: 10
    youtube: null    # wide net — no trim
    research: 6
    ...

validation:
  min_total_stories: 55
  min_categories: 12
  required_category_ids: [leaderboard, analytics, aisearch, youtube, ...]
```

### LLM model

**File:** `config.yaml` → `llm.model` (default `llama3.1:latest` on laptop; showcase `qwen3.6:35b` via Ollama).

---

## UI / card display

**File:** `vendor/ai-news-digest/digest-app.js`

| Element | Behavior |
|---------|----------|
| `story.url` | **Read source →** (YouTube chapter timestamp) |
| `story.links[]` | Pill links under summary — **GitHub ·**, **X ·**, **LinkedIn ·**, HF, arXiv, announcements (`kind` field) |
| YouTube sub-tabs | Channel filter row (All + per-channel) |

Styles: `vendor/ai-news-digest/styles/dark.css` (`.card-resource-link`).

---

## Quick tuning recipes

| Goal | Change |
|------|--------|
| More aisearch chapters in final digest | Raise `enrich.category_targets.aisearch` |
| Keep every YouTube topic | Leave `youtube: null` |
| Trim YouTube | Set e.g. `youtube: 15` |
| Stronger “name the repo” summaries | Edit `_skeleton_rules("youtube")` in `enrich.py` + `editorial_brief.md` |
| Better tool↔chapter matching | Edit `_TOPIC_RESOURCE_HINTS` in `youtube_channels.py` |
| Add a YouTube channel | `SECONDARY_CHANNELS` + run preflight |
| Softer prose | Edit **Prose style** in `editorial_brief.md` |
| Stricter gap URLs | Already strict; enable `enrich.tool_loop` for agentic verify |

---

## Rebuild one day after prompt/source changes

```bash
# Refresh preflight (network)
python vendor/ai-news-digest/scripts/preflight.py --prefix 20260703120000 --force

# Full pipeline (enrich + render, ~10–35 min depending on hardware)
python run.py --start 2026-07-03 --history 10
```

After render, rebuild archive sync:

```bash
python -c "from pipeline.config import load_config; from pipeline.render import rebuild_reports_archive; rebuild_reports_archive(load_config())"
```

---

## Diagnostics

Per-run LLM calls logged in `diagnostics/{prefix}.diagnostics.json` (`llm.calls[]` with `call_name` like `enrich.youtube.all`, `enrich.gap.analytics,agentic-ai,llm`).

Use these to see which prompt pass produced which category.
