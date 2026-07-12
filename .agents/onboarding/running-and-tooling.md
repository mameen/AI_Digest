# Running & Tooling

> **Canonical narrative:** [`README.md`](../../README.md) at the repo root. **If this
> doc conflicts with README, README wins.**

## Prerequisites

- Python venv: `python admin/manage.py bootstrap` (or `bootstrap --locked` for exact pins from `requirements-lock.txt`).
- `playwright install chromium` runs during bootstrap (for Crawl4AI leaderboard pages).
- After dependency changes: `python admin/manage.py freeze-requirements` (with green tests), then commit `requirements.txt` + `requirements-lock.txt`.
- Ollama running locally with the configured model (`llm.model` in
  `config.yaml`, default `llama3.1:latest` on laptop; showcase runs use
  `qwen3.6:35b`). No cloud keys needed.
- Hermes on PATH for production GO (`python agentic/hermes/admin/manage.py bootstrap`).

## Hermes gateway and redeploy

**First-time:** after `agentic/hermes/admin/manage.py bootstrap`, start the gateway
and open chat:

```bash
hermes gateway start
python agentic/hermes/admin/manage.py hermes dashboard
```

**After SOUL, role, tool, or kanban-patch changes**, redeploy profiles and restart
long-lived Hermes processes:

```bash
python agentic/hermes/admin/manage.py setup
hermes gateway restart
python agentic/hermes/admin/manage.py hermes dashboard   # reopen if already open
```

See [`agentic/hermes/admin/README.md`](../../agentic/hermes/admin/README.md) and
[`agentic/hermes/POC.md`](../../agentic/hermes/POC.md).

## Production GO (default)

```bash
python agentic/hermes/admin/manage.py go --start 2026-07-09 --history 10 --fresh
```

Requires Hermes gateway running. Pass: artifact gates, report HTML under
`agentic/hermes/reports/`, diagnostics waterfall.

Handover smoke (kanban, no HTML):

```bash
python agentic/hermes/admin/manage.py verify-handover
```

See [`agentic/hermes/POC.md`](../../agentic/hermes/POC.md) and
[`system_roles.md`](../../agentic/hermes/system_roles.md).

## Batch escape hatch (`go --pipeline` / `run.py`)

Debug or A/B against deprecated batch orchestration — **not** daily GO:

```bash
python agentic/hermes/admin/manage.py go --pipeline --start 2026-07-09 --skip-ingest
# or directly:
python run.py --start 2026-07-02 --history 10
```

- `--start DATE` — digest date (`YYYY-MM-DD` or `YYYYMMDD`); default is today UTC.
- `--history N` — editorial lookback in days (default from `run.history_days`).
- `--fetch-only` — stop after ingestion (writes cache/preflight only).
- `--skeleton-only` — skip the LLM enrich (promote the unscored skeleton).
- `--dry-run` — print resolved paths and exit.
- `--doctor` / `--skip-doctor` / `--force` — pre-run self-check controls.

A full run takes ~10-12 min and ~150-200k tokens; watch it in the diagnostics
waterfall afterwards.

## The pre-run self-check ("doctor", `pipeline/doctor.py`)

Runs before a long job: verifies Ollama + model are reachable, enrich deps are
importable, output dirs are writable, and (optionally) that sources respond.
Blocking failures stop the run unless `--force`; soft issues warn and proceed.
Run it standalone with `python run.py --doctor`.

## Re-render WITHOUT re-running the LLM (the common, cheap path)

When you only changed the **widget, CSS, template, or rendering logic**, do NOT
re-run the pipeline (that re-invokes the LLM and can change/degrade content).
Re-render deterministically from the existing JSON instead:

```powershell
python -c "import json; from llm_pipeline.config import load_config; from llm_pipeline.render import render; cfg=load_config(); p='20260702120000'; render(cfg, p, json.load(open('reports/'+p+'.json',encoding='utf-8')))"
```

This re-stamps `generator_version` (release line + same prefix), re-inlines the
current widget into `<prefix>.html`, and rebuilds `reports/index.{json,html}`.
Story content is preserved verbatim. Leaderboard blocks are preserved from the
existing HTML (and refreshed from cache if a crawl exists).

**Archive-only rebuild** (heatmap, themes, nav, footer — no per-digest JSON change):

```powershell
python -c "from llm_pipeline.config import load_config; from llm_pipeline.render import rebuild_reports_archive; rebuild_reports_archive(load_config())"
python -c "from llm_pipeline.config import load_config; from llm_pipeline.paths import diagnostics_dir; from llm_pipeline.diagnostics_frame import rebuild_diagnostics_archive; from llm_pipeline.diagnostics import rebuild_diagnostics_waterfall_pages; cfg=load_config(); d=diagnostics_dir(cfg); rebuild_diagnostics_waterfall_pages(d); rebuild_diagnostics_archive(d, cfg)"
```

Do **not** call `build_frame_html()` directly — see `debugging-and-pitfalls.md`.

## Testing (`run_tests.py`)

```powershell
python run_tests.py
```

Runs Python `unittest` discovery under `tests/` **and** `node --test` over the
widget, reporting a combined PASS/FAIL. Node tests are skipped with a notice if
`node` is not on PATH. Policy: **real fixtures, no mocks** — see `.agents/AGENTS.md`.

> PowerShell note: piping `run_tests.py` through `Select-Object`/`Select-String`
> can surface a non-zero exit from the *pipe*, not the tests. If the summary says
> `python: PASS / node: PASS`, re-run the bare command to confirm the true code.

## Module map (where things live)

| Area | Module(s) |
|---|---|
| Orchestration / CLI | `run.py` |
| Config load | `pipeline/config.py`, `config.yaml` |
| Run window / prefix | `pipeline/dates.py` |
| Ingest | `pipeline/fetch.py`, `vendor/.../scripts/preflight.py`, `fetch_*.py` |
| Leaderboard parse (crawl) | `pipeline/leaderboards.py` |
| Leaderboard parse (API) | `pipeline/structured_sources.py` |
| Enrich (multi-pass LLM) | `pipeline/enrich.py` |
| LLM client / Instructor | `pipeline/llm_client.py` |
| Agentic link tools | `pipeline/tools.py` |
| Prior-digest carry-forward | `pipeline/history.py` |
| Grounding self-check | `pipeline/grounding.py` |
| Validation | `pipeline/validate.py` |
| Schemas | `pipeline/schema.py` |
| Render / index / frames | `pipeline/render.py`, `frame_*.py`, `site_footer.py` |
| Diagnostics | `pipeline/diagnostics.py`, `diagnostics_frame.py` |
| Visualizations | `pipeline/visualize.py` |
| Version | `pipeline/__init__.py` (`__version__`, `generator_version`) |
| Browser widget | `vendor/ai-news-digest/digest-app.js` + `content.template.html` |

## Outputs

| Path | Contents | Tracked? |
|---|---|---|
| `reports/` | digest JSON/HTML + `index.html` archive | yes |
| `diagnostics/` | timing/token telemetry + archive frame | yes |
| `.preflight/` | raw preflight JSON | yes |
| `.cache/` | Crawl4AI + structured prefetch | no (gitignored) |

## Deploy

GitHub Pages serves from `main` (`reports/index.html` is the entry). Work on a
branch, get explicit approval, then merge/push to `main` to publish.

---

## Agentic Hermes modules

> Production GO details: root README and [`system_roles.md`](../../agentic/hermes/system_roles.md).

### Key modules

| Area | Module(s) |
|---|---|
| Production GO | `agentic/hermes/admin/manage.py` `cmd_go_agents` |
| Batch escape hatch | `agentic/hermes/tools/pipeline_go.py` |
| Orchestration | `agentic/hermes/admin/manage.py` |
| Shared ingest | `lib/ingest/stage1.py` |
| Grounding / validate / render | `llm_pipeline/` (shared libs) |
| Worker tools | `agentic/hermes/plugins/digest-tools/` |
