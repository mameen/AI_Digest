# Debugging, Tracing & Recurring Pitfalls

This is the "when it breaks" doc — the failures that have actually bitten this
project, how to spot them, and the fix that worked.

## How to debug a run

1. **Diagnostics waterfall** — open `diagnostics/<prefix>.diagnostics.html` (or
   the archive at `diagnostics/index.html`). Each stage shows timing, token
   share, and a FAILED/degraded marker. `diagnostics/<prefix>.run.log` has the
   plain-text log.
2. **Inspect the JSON directly** — the report JSON is the ground truth. A quick
   Python one-liner over `reports/<prefix>.json` gives story counts, per-category
   coverage, provenance histogram, and missing-field checks.
3. **Non-degraded bar** — before publishing, confirm the run still clears
   `validation` in `config.yaml` (≥55 stories, 11/11 required categories) and
   that no category was zeroed.

## How to trace a story to its origin (auditability)

Every published story carries a deterministic `provenance` token in the JSON and
a clickable `(i)` popover in the UI (id · via · source · url · carried):

| token | meaning |
|---|---|
| `skeleton:<cat>` | curated preflight feed |
| `crawl:leaderboard` | parsed from crawled leaderboard markdown |
| `gap:<cat>` | LLM gap-fill |
| `gap-refill:<cat>` | per-category refill retry |
| `carry:<prefix>` | carried forward from a prior digest |

If a claim and its cited source disagree, the token tells you which stage
introduced it. Note the known limitation: **second-degree mining** (a primary
source hinting at a secondary source) is not yet handled — the trace stops at the
stage that produced the story.

## Recurring pitfalls (symptom → cause → fix)

**LLM fabricates provenance / invents its own origin.**
Cause: provenance was exposed on the LLM response model. Fix: `StoryEnrich` has
**no** `provenance` field; it is stamped deterministically post-enrich via
`_with_provenance`. Never re-add it to the response model.

**Fabricated or dead article links in gap categories.**
Cause: gap categories have no scraped feed, so the model invents plausible deep
paths or cites leaderboard roots. Fix: the deterministic grounding guard
(`pipeline/grounding.py`) demotes ungrounded links (`url → None`,
`source_pending`) while keeping the topic. Optionally enable the `tool_loop` to
verify/repair links first.

**A required category comes back empty (local model zeroed it).**
Cause: small local models occasionally drop a whole category. Fix: `gap_fill_retries`
re-asks each empty category alone; `carry_forward` seeds any still-empty required
category from the most recent in-window prior digest (verified links,
`carried_forward` flag).

**`IncompleteOutputException` (output incomplete due to max_tokens) on a heavy
enrich batch (typically `robotics`).**
Cause: the batch prompt (stories JSON + brief + rules) overflows Ollama's
**context window**, leaving too few tokens for the structured JSON reply, which is
truncated mid-output. Ollama's default window is **VRAM-tiered** (4k <24 GiB,
**32k for 24-48 GiB**, 256k >=48 GiB), so a 24-48 GiB GPU defaults to 32,768; the
robotics batch grew to ~28k tokens per 18-story batch once `raw_snippet` (2000
chars) + `links[]` landed in commit `7dd02a5`, leaving too little headroom. Fix:
raise the window on the **Ollama server** — do **not** try a per-request `num_ctx`.
The OpenAI-compat `/v1` endpoint (which Instructor requires) **ignores** it in
every form (`options.num_ctx`, top-level `num_ctx`, `context_length`); only native
`/api/chat` honours it (empirically verified). Set `OLLAMA_CONTEXT_LENGTH=65536`
on the server and restart it. On the **Windows app**, run `setx /m
OLLAMA_CONTEXT_LENGTH 65536` in an *elevated* console, then Quit + relaunch the
tray app so `ollama.exe` inherits it; the app's Settings "Context length" slider is
**greyed out whenever the env var is set** (expected — the env var wins). Verify
with `ollama ps` (the `CONTEXT` column reads 65536 after a load). A Modelfile-baked
`PARAMETER num_ctx` also works on `/v1` but changes the model name. Alternatively,
trim the prompt to fit 32k (cap `raw_snippet` sent to enrich, or lower
`enrich.stories_per_batch`).

**A UI/widget change "doesn't show up" in a report.**
Cause: report HTML **embeds** the widget JS/CSS at render time; existing pages
keep the old widget. Fix: re-render the report (see running-and-tooling.md) — do
*not* re-run the LLM for a cosmetic change.

**Archive `index.html` is missing nav, author card, footer, or shows `__AUTHOR_CARD__`.**
Cause: calling `build_frame_html()` (or `build_diagnostics_frame_html()`) alone
only fills template placeholders — it does **not** inject chrome. A manual
one-liner rebuild is a common footgun. Fix: always use the full rebuild helpers:

| Page | Function |
|---|---|
| Reports archive | `pipeline.render.rebuild_reports_archive(cfg)` |
| Diagnostics archive | `pipeline.diagnostics_frame.rebuild_diagnostics_archive(diag_dir, cfg)` |
| Per-run waterfall HTML | `pipeline.diagnostics.rebuild_diagnostics_waterfall_pages(diag_dir)` |

Each archive rebuild runs, in order: build frame HTML → `inject_author_card` →
`inject_frame_nav` → `inject_site_footer` → `assert_archive_html_ready` (fails if
any `__AUTHOR_CARD__` or other placeholder leaked). After a manual rebuild, grep
the output for `__AUTHOR_CARD__`, `<div class="frame-controls">`, and
`<footer class="site-footer">`.

**Duplicate theme toggle inside the diagnostics iframe (or per-digest HTML).**
Cause: embedding pages must use `theme-apply.js` (apply `data-theme` only), not
full `theme.js` (mounts controls). The parent archive frame keeps `theme.js` in
`.frame-controls`. Fix: waterfall pages via `_render_waterfall_html`; per-digest
pages via `build_content_html` / `theme_apply_js()`. Parent syncs iframe theme
on toggle and iframe load.

**Version bumped without permission.**
Rule: only the **build segment** (the run prefix `YYYYMMDDHHmmss`) changes
automatically. **MAJOR.MINOR** bumps require explicit maintainer approval. When
approved, bump `__version__` in `pipeline/__init__.py` once, deliberately.

**Diagnostics footer version drifts after a bump.**
Cause: `render()` re-stamps reports + index, but not diagnostics HTML footers.
Fix: if you bump MAJOR.MINOR, re-stamp the diagnostics footers too so `v<line>`
is consistent across reports, index, and diagnostics.

**Historical report fails a version test after a code bump.**
Cause: a committed report keeps the version that produced it. Fix: version tests
assert *format + own-run-prefix traceability*, not equality with the current
release line (`tests/test_version.py`). Don't re-stamp old reports.

**A "leaderboard API" URL returns HTML/404/garbage.**
Rule: several circulated leaderboard endpoints are dead or fabricated. **Probe
live before wiring** any source into `structured_sources.py`; only add it after a
real request returns usable JSON.

**`run_tests.py` shows PASS but a non-zero exit in PowerShell.**
Cause: piping through `Select-Object`/`Select-String` reports the pipe's exit,
not the test process. Fix: re-run the bare `python run_tests.py` to read the true
exit code.

**Windows CRLF↔LF warnings on commit.**
Harmless: Git normalizes line endings for tracked report/HTML files. No action
needed.

## Proposing a fix (the reflex)

When you find a bug: reproduce it against a real fixture, add/extend a
fixture-backed test that fails, then fix the code until it passes. Never assert
against hand-written strings divorced from real data. After the fix, run the full
`python run_tests.py` and, if a report is involved, regenerate and re-check the
non-degraded bar before considering it done.
