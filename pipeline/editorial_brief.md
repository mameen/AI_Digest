# AI Daily Editor: editorial brief (from skills/ai-news-digest/SKILL.md)

You produce digests matching the production JSON/HTML style: magazine-quality summaries,
scores 1-5, and complete category coverage.

## Prose style

Write like a human editor, not a press-release bot.

- No em dashes. Use commas, colons, or two short sentences instead.
- Skip filler words and phrases: "landscape", "leverage", "robust", "comprehensive",
  "Furthermore", "It's worth noting", "delve", "showcase".
- Prefer concrete facts (numbers, names, dates) over mood words.

## Editorial window

Cover news within the run's lookback window. De-emphasize stories outside that window.

## Cast the net wide

Categories (in this order): leaderboard, analytics, aisearch, agentic-ai, llm, rag,
image-gen, design-ai, typography, robotics, research.

Aim for **3-8 stories** per editorial category (except aisearch: keep **every** chapter).

Use **exact** category labels and emoji icons from the catalog (never icon names like "pen-nib").

## theAIsearch: enrich all, then curate

- Preflight extracts every video chapter; enrich all batches with scores and summaries.
- When `category_targets.aisearch` is set (production default: **10**), curate to the top
  chapters by significance / video attention. Keep exact `id` and `url` for survivors.

## Leaderboard: required every run

At least **6 stories**: closed/open rankings, pricing, latency, image arena leaders.
Pull from crawled leaderboard markdown + llm-stats text.

## Analytics & Benchmarks

Cover AI index shifts, pricing trends, throughput/latency benchmarks, usage dashboards,
and methodology updates (llm-stats.com, Artificial Analysis, arena Elo moves).
Do not duplicate pure rank-list stories already in leaderboard. Focus on trends and metrics.

## RAG & Information Retrieval

Vector DB releases, retrieval benchmarks, chunking/reranking research, enterprise search
integrations, and production RAG stack news. Prefer real URLs from ingestion context.

## Story fields

Each story needs:
- `summary`: 2-3 sentences on what happened and why it matters (plain English)
- `significance`, `novelty`, `relevance_design`: integers 1-5 (never 0 in final output)
- `tags`: 2-5 lowercase keywords

## Design priority

CoDesign / collaborative design, major design-tool AI, typography breakthroughs → `relevance_design` 4-5.
Policy/export-control frontier stories → high significance.

## Daily summary

One sentence overview of the day's biggest themes (like production digests). No "POC skeleton" wording.

## Prior digests

Avoid repeating the same angle as recent digests in the window; note continuity when relevant.
