# Agent Code Guide

Working notes for agents (and humans) contributing to this repo. Keep changes
conservative and in keeping with the surrounding code.

> **Single entry point.** This file lives at `.agents/AGENTS.md` (source of truth);
> repo-root `AGENTS.md` is a symlink for tools that only read the root. The deeper
> onboarding narrative lives under `.agents/onboarding/`. **Product narrative:**
> [`README.md`](../README.md) at the repo root — if anything conflicts, README wins.

## Repository layout

```
AI_Digest/                          ← ORIO: agentic daily AI news digest
├── README.md                       ← Product story, ORIO roles, evolution (canonical)
├── AGENTS.md → .agents/AGENTS.md   ← Agent rulebook (symlink to source of truth)
│
├── .agents/                        ← Agent onboarding & rules (source of truth)
│   ├── README.md                   ← Layout, symlinks, reading order
│   ├── AGENTS.md                   ← This file — day-to-day rules
│   ├── onboarding/                 ← Full narrative docs
│   │   ├── architecture.md         ← Architecture & design summary
│   │   ├── running-and-tooling.md  ← How to run; what each tool/module does
│   │   ├── debugging-and-pitfalls.md
│   │   ├── principles-and-workflow.md
│   │   └── hermes-and-repo.md      ← Hermes profiles: env, imports, secrets
│   └── .cursor/rules/              ← Cursor rules (symlinked to root)
│
├── agentic/                        ← Agentic layer (4 branches)
│   ├── hermes/                     ← Multi-agent crew (active production)
│   │   ├── admin/                  ← Gateway, SOUL configs, roles
│   │   ├── tools/                  ← Agent tool implementations
│   │   ├── plugins/                ← Hermes plugins
│   │   └── docs/                   ← Architecture, POC, Slack integration
│   ├── kaggle_ai_agents/           ← Training project (incomplete)
│   │   ├── day_1 … day_5/          ← Daily exercises
│   │   ├── submission/             ← Kaggle submissions
│   │   └── capstone_project/       ← Capstone work
│   └── single_hermes_agent/        ← Single-agent-with-skills (active direction, in progress)
│
├── llm_pipeline/                   ← Legacy staged pipeline (ingest → enrich → validate → render)
│   ├── fetch.py                    ← Source fetching (YouTube, RSS, web crawls)
│   ├── editorial.py                ← Editorial brief assembly
│   ├── enrich.py                   ← Story enrichment & grounding
│   ├── render.py                   ← HTML/JSON report rendering
│   ├── leaderboards.py             ← Leaderboard data injection
│   ├── vendor/                     ← Third-party widgets (digest-app.js, templates)
│   └── admin/                      ← Admin server & diagnostics
│
├── pipeline/                       ← Mirror of llm_pipeline (active code path)
│   └── [same files as llm_pipeline/]
│
├── app/                            ← Deployed site assets (index.html, reports, diagnostics)
├── lib/                            ← Shared utilities (deploy_app.py, paths, schema)
├── config/                         ← Project configuration (paths.yaml)
├── scripts/                        ← Standalone scripts (audit_secrets.py, deploy_app.py)
├── tests/                          ← Python + Node test suite
├── docs/                           ← General documentation
├── admin/                          ← Admin CLI (manage.py, README.md)
├── run.py                          ← Production entry point
├── run_tests.py                    ← Combined Python + Node test runner
└── .cache/                         ← Prefetched data (gitignored)
```

**Key:** `agentic/hermes/` + `pipeline/` = current production path. `llm_pipeline/` is legacy.

## Principles

1. **Showcase-grade engineering.** Portfolio-visible project — hold a high bar
   for correctness, consistency, and discipline in every change.
2. **Simple, but considered.** Keep the design simple *and* weigh at least three
   valid options before a non-trivial approach; record why the chosen one won.
3. **Disciplined local workflow.** Describe → lint → test → version (build
   segment auto; MAJOR.MINOR only with maintainer approval) → commit on a branch.
   Never push without explicit permission; `main` is protected.
4. **Honest, auditable data.** Every published story must be true, accurate, and
   traceable to its origin (deterministic `provenance` token in JSON + a
   clickable trace in the UI). Never ship a fabricated link.
5. **Self-check and reflect.** After a change, regenerate, inspect for
   degradation, and reason about whether the goal was met — green tests alone
   don't mean a good report.

Full detail: `.agents/onboarding/principles-and-workflow.md`.

## Onboarding docs

| I want to… | Read |
|---|---|
| Understand the whole system | `.agents/onboarding/architecture.md` |
| Run it / know what a module does | `.agents/onboarding/running-and-tooling.md` |
| Debug a failure or trace a story | `.agents/onboarding/debugging-and-pitfalls.md` |
| Know the rules before I touch code | `.agents/onboarding/principles-and-workflow.md` |
| Hermes profile: repo, env, imports, secrets | `.agents/onboarding/hermes-and-repo.md` |

## Hermes profiles & agent repo rules

**All `orio_*` Hermes profiles** must follow [`.agents/onboarding/hermes-and-repo.md`](onboarding/hermes-and-repo.md)
— referenced from each profile SOUL and copied to `~/.hermes/profiles/<role>/REPO_ONBOARDING.md`
on `manage.py setup`. When import, env, git, or secrets questions come up in chat, **`read_file` that
doc before guessing** (do not infer PYTHONPATH, pip install, or missing `__init__.py` without it).

| Topic | Rule |
|---|---|
| **Imports under Hermes** | `digest-tools` overlays `agentic/hermes/tools/*.py` as `tools.*`; preload deps include `profiles`, `artifacts`, `runtime_store`. `manage.py` uses normal imports via `sys.path`. |
| **Redeploy after code/SOUL changes** | `python agentic/hermes/admin/manage.py setup` → `hermes gateway restart` → reopen dashboard if needed. |
| **Secrets** | Pre-commit: `audit_secrets.py` on staged files. Never commit `.env`, tokens, or credentials. Exemptions: `.gitleaksignore`. Install hooks: `./.githooks/install.sh`. |
| **Git (Concierge)** | `digest_publish` only — fixed paths, commit, push only with `confirm_push: true` after explicit user approval. No branch/status/diff tools. |
| **Git (maintainers)** | Branch → test → PR; never push without permission; no agent co-author trailers. |
| **Sister project** | **Project Career Zazu** (`job-ai-sistant` repo) mirrors this `.agents/` layout — separate product, same Hermes onboarding pattern. |

Quick notes: the repo is self-contained (local Ollama + Instructor, no cloud
keys); prefer **re-render over re-run** for UI/render-only changes; reports are
traced by run-prefix and never re-stamped to the current code line.

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

## Post-change workflow

After any **major change** (pipeline logic, a parser, the widget, schema, or a
source), run this loop in order — no shortcuts:

1. **Regenerate** the latest report — production path:
   `python agentic/hermes/admin/manage.py go --start <date> --fresh`. Batch escape
   hatch only: `python run.py --start <date>`. Confirm it is *not* degraded (story
   count and per-category coverage hold up); never publish a degraded showcase report.
2. **Lint + test** — `python run_tests.py` must be green (Python + Node).
3. **Push to a relevant branch, never `main`.** Reuse an existing topic branch
   where it fits, otherwise cut a fresh one (`chore/…`, `fix/…`, `feat/…`).
4. **Ask permission before pushing.** State what will be pushed and wait for an
   explicit yes; the maintainer may approve or decline.

`main` is a protected, always-shippable branch — work happens on branches and
merges via PR.

## Versioning

A single human-readable version, more traceable at a glance than a commit hash.

- **Source of truth:** `__version__` in `pipeline/__init__.py`, the release line
  `MAJOR.MINOR` (major = breaking pipeline/schema change, minor = new
  feature/source).
- **Bump deliberately**, once per meaningful change — *not* automatically per
  step (the run timestamp already moves every run, so auto-bumping adds churn
  without meaning).
- **The run prefix is the third segment**, appended after the release line:
  `0.4.20260630120000` reads as "code v0.4 produced the 20260630120000
  report". Do not invent a second timestamp — reuse the run prefix.
- **Surface it** as `generator_version` in the report JSON (release line + run
  prefix); the report + diagnostics footer shows the bare release line `v0.4`.
- **Tag releases** `vMAJOR.MINOR` so `git describe` gives readable names and the
  version↔hash link is preserved.

## Commit / push

- Commit locally with a descriptive message. **Do not push** unless explicitly
  asked (see the post-change workflow above).
- **Never** add `Co-authored-by` automation trailers or any third-party co-author
  line to commit messages. Commits are **maintainer-only** for attribution and
  GitHub contributors. `.githooks/` strips and rejects these when
  `core.hooksPath` is set (run `./.githooks/install.sh` once per clone).
- Never commit secrets. The `.cache/` prefetch is gitignored; `reports/`,
  `diagnostics/`, and `.preflight/` are tracked. **Pre-commit** (`.githooks/`)
  runs `scripts/audit_secrets.py --staged` to block API keys, `.env` files,
  and other credentials in newly staged lines.
