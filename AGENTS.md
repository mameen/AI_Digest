# Agent Code Guide

Working notes for agents (and humans) contributing to this repo. Keep changes
conservative and in keeping with the surrounding code.

## Testing policy

**Test the real thing. Avoid mocks.** Prefer exercising real code paths against
real data; where live calls are impractical, use committed **test data /
fixtures** rather than stubbing behaviour.

- **No mocking** of our own functions, the network, or the filesystem unless
  there is genuinely no alternative. If you reach for a mock, first ask whether
  a small real fixture would do the job instead.
- **Use real fixtures.** Network-derived data is captured once (trimmed) and
  committed under `tests/data/`, then parsed by the *actual* production code.
  Examples: `artificialanalysis.ai_leaderboards_models.md` (crawl markdown),
  `evalplus_results.json`, `swebench_leaderboards.json` (structured APIs).
- **Test each layer in the runtime it actually runs in:**
  - Python pipeline (`pipeline/*.py`) → `unittest` under `tests/`.
  - Browser widget (`vendor/ai-news-digest/digest-app.js`) → `node --test`. The
    widget's pure logic is exported behind a
    `if (typeof module !== 'undefined' && module.exports)` guard so Node can
    import it with no DOM and no mocks.
- **Run everything with one command:**
  ```
  python run_tests.py
  ```
  It runs Python `unittest` discovery and `node --test` over the widget, and
  reports a combined PASS/FAIL. (Node tests are skipped with a notice if `node`
  is not on PATH.)
- **When you change a parser or the widget, add/extend a fixture-backed test**
  rather than asserting against hand-written expected strings divorced from real
  data.

## Leaderboard source kinds

The `leaderboards` widget (the `const leaderboards = {…}` object in
`vendor/ai-news-digest/template.html`) is **data-driven at build time**, never
hand-edited for fresh rankings. Two source kinds feed it:

1. **Crawl sources** — JS-rendered pages with no public API. Listed in
   `REQUIRES_WEB_FETCH` (`vendor/ai-news-digest/scripts/preflight.py`), fetched
   by Crawl4AI into `.cache/<prefix>/crawl/*.md`, then parsed by
   `pipeline/leaderboards.py` (e.g. the AA Intelligence table).

2. **Structured-API sources** — endpoints that publish structured JSON, so they
   need fetching but **no scraping**. Registered in
   `pipeline/structured_sources.py` (`STRUCTURED_SOURCES`), fetched into
   `.cache/<prefix>/structured/*.json`, parsed into rows, and injected into
   their tabs. Verified live endpoints: SWE-bench
   (`.../swe-bench.github.io/master/data/leaderboards.json`) and EvalPlus
   (`evalplus.github.io/results.json`). Toggle via
   `ingestion.structured_sources.enabled` in `config.yaml`.

Both kinds are applied at render time in `pipeline/render.py`
(`_crawl_driven_leaderboards`), which overwrites the template's *seed* rows with
the run's live data so a tab is never stale. Seed rows in `template.html` are a
realistic fallback for when no fetch is available.

> Verify before wiring. Several "leaderboard API" URLs circulated externally are
> dead or fabricated (probe everything first). Only add a source after a live
> request returns usable JSON.

## Commit / push

- Commit locally with a descriptive message. **Do not push** unless explicitly
  asked.
- Never commit secrets. The `.cache/` prefetch is gitignored; `reports/`,
  `diagnostics/`, and `.preflight/` are tracked.
