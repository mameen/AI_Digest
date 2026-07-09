# Architecture & Design Summary

AI Digest is a **local-first, staged pipeline** that ingests public AI-news
sources, enriches them with a local LLM, guards their accuracy, and publishes an
interactive HTML archive with per-run diagnostics. Everything runs on one
workstation (Ollama + Instructor); no cloud keys are required.

## The four stages

`run.py` orchestrates a strict `ingest → enrich → validate → render` flow. Each
stage is wrapped in a diagnostics `collector.stage(...)` context so timings,
token counts, and failures are captured for the waterfall.

```
run.py
 ├─ [1] Ingest    preflight skeleton (curated feeds) + Crawl4AI leaderboards
 │                + structured-API leaderboards (SWE-bench, EvalPlus)
 ├─ [2] Enrich    multi-pass local LLM: summarize, score, gap-fill, curate,
 │                (optional) tool-loop link repair, carry-forward
 ├─ [3] Validate  category counts, significance, grounding guard
 └─ [4] Render    digest JSON → HTML + reports/index.html + diagnostics/*
```

## Stage 1 — Ingest (`pipeline/fetch.py`, `vendor/.../scripts/preflight.py`)

- **Preflight** builds a *skeleton*: curated per-category feeds (theAIsearch
  chapters, typography, research, robotics, llm-stats) parsed into story stubs.
- **Crawl sources** — JS-rendered leaderboard pages with no API are fetched by
  Crawl4AI into `.cache/<prefix>/crawl/*.md`, then parsed by
  `pipeline/leaderboards.py`.
- **Structured-API sources** — endpoints publishing JSON (registered in
  `pipeline/structured_sources.py`) are fetched into `.cache/<prefix>/structured/`
  and parsed into rows. Toggle via `ingestion.structured_sources.enabled`.

## Stage 2 — Enrich (`pipeline/enrich.py`)

Multi-pass, orchestrated by `enrich_digest` → `_enrich_multipass`:

- **Pass 1 — skeleton categories:** score + summarize curated stories in batches
  (`stories_per_batch`), then curate to `category_targets`. Stamped
  `skeleton:<cat>`.
- **Pass 2 — leaderboard:** the crawled leaderboard markdown becomes stories,
  stamped `crawl:leaderboard`.
- **Pass 3 — gap fill:** categories with no scraped feed (analytics, agentic-ai,
  llm, rag, image-gen, design-ai, robotics) are filled by the LLM in chunks
  (`gap_categories_per_call`), stamped `gap:<cat>`; empty categories are re-asked
  (`gap_fill_retries`), stamped `gap-refill:<cat>`.
- **Tool loop (optional, default-off):** the model may call `verify_url` /
  `web_search` (`pipeline/tools.py`) to check and repair gap links before the
  deterministic guard runs.
- **Carry-forward (safety net):** if a required category is still empty, seed it
  from the most recent in-window prior digest (already-verified links), stamped
  `carry:<prefix>` and flagged `carried_forward`.
- **Pass 4 — daily summary** + aisearch video metadata.

If `llm.enabled` is false, `_promote_skeleton` publishes the unscored skeleton.

## Stage 3 — Validate (`pipeline/validate.py`, `pipeline/grounding.py`)

- **Grounding guard** is the pipeline's deterministic *self-check*: a story whose
  `url` is a bare domain, a known leaderboard *root*, or (when an ingestion
  allow-set is supplied) a URL the model was never shown is **ungrounded**. The
  guard *keeps the topic* but demotes the link (`url → None`, `source_pending`)
  so a real development is never lost to a fake link. The `leaderboard` category
  legitimately cites roots and is exempt.
- **Validation** checks `min_total_stories`, `min_categories`, and
  `required_category_ids` (see `config.yaml`).

## Stage 4 — Render (`pipeline/render.py`)

- Writes the digest JSON (stamping `generator_version = <release>.<prefix>`),
  then inlines the browser widget (`vendor/ai-news-digest/digest-app.js`) and
  content template into `<prefix>.html`.
- Rebuilds `reports/index.json` + `reports/index.html` (the archive frame with
  the latest digest embedded, heatmap, nav, author card, site footer).
- `_crawl_driven_leaderboards` overwrites the template's seed leaderboard rows
  with the run's live crawl + structured data so a tab is never stale.

## Data model (`pipeline/schema.py`)

- `Story` is the published shape: `id, title, summary, source, url?,
  significance(1-5), novelty, relevance_design, tags[], image_url?,
  source_pending, provenance?`.
- `StoryEnrich` is the **LLM response** model — deliberately identical *except it
  has no `provenance`*. Provenance is deterministic pipeline metadata stamped
  after enrich (`_with_provenance`); the model must never author its own origin.
- `CategoryStories` / `GapCategories` / `DigestHeader` are the structured-output
  envelopes Instructor validates each LLM call against.

## The browser widget (`vendor/ai-news-digest/`)

- `digest-app.js` renders cards, filters, donut/significance/tag charts, the
  leaderboard tabs, the provenance `(i)` popover, and the one-click copy icon.
  Pure logic is exported behind a `module.exports` guard so Node can unit-test it
  with no DOM (`digest-app.test.js`).
- `content.template.html` holds the card CSS; `frame.html` is the archive shell.
- `scripts/_report_utils.py` + `rebuild_index.py` build the HTML/index; the
  `pipeline/render.py` layer wraps them for the staged run.

## Key design decisions (and the options weighed)

- **Local LLM over cloud API:** reproducible, key-free, portfolio-friendly.
  (Options: cloud API — cost/keys; no LLM — too shallow; local Ollama — chosen.)
- **Deterministic guard over a second LLM judge:** offline models can't reliably
  tell a real link from a convincing fake, so grounding is rule-based and
  auditable. (Options: LLM self-critique; human review; deterministic guard —
  chosen for honesty + repeatability.)
- **Re-render decoupled from re-enrich:** UI/render changes ship via a
  deterministic re-render of existing JSON, never a fresh LLM run, so a good
  report is never risked for a cosmetic change.
- **Provenance as pipeline metadata, not model output:** guarantees the trace is
  trustworthy and can't be hallucinated.

## Agentic Hermes (`agentic/hermes/`)

A second orchestration path reuses the same schemas, grounding, validate, and
render modules — but fans work across Hermes kanban workers instead of sequential
`run.py` stages.

```mermaid
flowchart LR
    subgraph batch [llm_pipeline run.py]
        I1[ingest] --> E1[enrich] --> V1[validate] --> R1[render]
    end

    subgraph agentic [agentic/hermes manage.py go]
        R2[researcher × N] --> L2[librarian] --> S2[synthesizer]
        S2 --> V2[validate] --> R2b[render]
    end

    OUT[(llm_pipeline/reports/)]
    R1 --> OUT
    R2b --> OUT
```

| Stage | `run.py` | Agentic workers |
|---|---|---|
| Ingest | Batch preflight + crawl + structured | Per-topic lazy tools on cache miss |
| Enrich / merge | In-process Instructor passes | Librarian + `synthesize_digest` workers |
| Invariants | grounding + validate | Same code paths |
| Output | `reports/<prefix>.html` | Same |

Deep dive: [`agentic/hermes/docs/ARCHITECTURE.md`](../../agentic/hermes/docs/ARCHITECTURE.md).
E2E runbook: [`agentic/hermes/HANDOFF.md`](../../agentic/hermes/HANDOFF.md).
