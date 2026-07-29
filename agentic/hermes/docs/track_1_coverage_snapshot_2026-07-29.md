# Track 1 Coverage Snapshot — 2026-07-29

**Run:** `coverage run -m unittest discover -s llm_pipeline/tests -t .`  
**Scope:** `llm_pipeline/**/*.py` + `lib/**/*.py`  
**Threshold:** 80% (fail-under configured in pyproject.toml)

---

## Overall

| Metric | Value |
|--------|-------|
| **Total statements** | 4,214 |
| **Uncovered** | 1,679 |
| **Branches** | 1,274 total, 175 partial |
| **Coverage** | **57%** |

---

## Core Pipeline Modules (llm_pipeline/)

| Module | Stmts | Miss | Cover | Status |
|--------|------:|-----:|------:|--------|
| `llm_pipeline/__init__.py` | 3 | 0 | 100% | OK |
| `llm_pipeline/config.py` | 5 | 0 | 100% | OK (shim) |
| `llm_pipeline/dates.py` | 5 | 0 | 100% | OK (shim) |
| `llm_pipeline/schema.py` | 5 | 0 | 100% | OK (shim) |
| `llm_pipeline/paths.py` | 5 | 0 | 100% | OK (shim) |
| `llm_pipeline/grounding.py` | 114 | 12 | 84% | OK |
| `llm_pipeline/leaderboards.py` | 5 | 0 | 100% | OK (shim) |
| `llm_pipeline/structured_sources.py` | 5 | 0 | 100% | OK (shim) |
| `llm_pipeline/styles.py` | 25 | 0 | 100% | OK |
| `llm_pipeline/tools.py` | 5 | 0 | 100% | OK (shim) |
| `llm_pipeline/doctor.py` | 142 | 30 | 77% | ⚠️ below 80% |
| `llm_pipeline/editorial.py` | 152 | 21 | 83% | OK |
| `llm_pipeline/enrich.py` | 320 | 241 | 23% | 🔴 critical gap |
| `llm_pipeline/frame_author.py` | 60 | 4 | 91% | ✅ improved from 73% |
| `llm_pipeline/history.py` | 48 | 4 | 90% | ✅ improved from 92% (slight drift) |
| `llm_pipeline/diagnostics.py` | 413 | 157 | 58% | ⚠️ below 80% |
| `llm_pipeline/environment.py` | 181 | 69 | 56% | ⚠️ below 80% |
| `llm_pipeline/diagnostics_frame.py` | 121 | 23 | 73% | ⚠️ below 80% |
| `llm_pipeline/validate.py` | 38 | 11 | 65% | ⚠️ below 80% |
| `llm_pipeline/render.py` | 81 | 64 | 18% | 🔴 largely untested |
| `llm_pipeline/frame_html.py` | 6 | 1 | 75% | OK |
| `llm_pipeline/frame_nav.py` | 48 | 13 | 68% | ⚠️ below 80% |
| `llm_pipeline/site_footer.py` | 26 | 2 | 91% | OK |
| `llm_pipeline/llm_client.py` | 50 | 43 | 11% | 🔴 untested (LLM calls) |
| `llm_pipeline/admin_frame.py` | 44 | 44 | 0% | N/A (admin-only) |
| `llm_pipeline/admin_ops.py` | 267 | 267 | 0% | N/A (admin-only) |
| `llm_pipeline/admin_server.py` | 3 | 3 | 0% | N/A (admin-only) |
| `llm_pipeline/local_server.py` | 181 | 181 | 0% | N/A (server-only) |
| `llm_pipeline/fetch.py` | 2 | 2 | 0% | N/A (unused?) |
| `llm_pipeline/run.py` | 111 | 111 | 0% | N/A (entry point) |
| `llm_pipeline/run_admin.py` | 15 | 15 | 0% | N/A (admin entry) |

---

## Lib Modules (lib/)

| Module | Stmts | Miss | Cover | Status |
|--------|------:|-----:|------:|--------|
| `lib/__init__.py` | 5 | 0 | 100% | OK |
| `lib/config.py` | 52 | 3 | 92% | ✅ |
| `lib/dates.py` | 39 | 0 | 100% | ✅ |
| `lib/schema.py` | 65 | 0 | 100% | ✅ |
| `lib/paths.py` | 62 | 8 | 81% | ✅ |
| `lib/tools.py` | 187 | 23 | 89% | ✅ |
| `lib/leaderboards.py` | 139 | 17 | 86% | ✅ |
| `lib/structured_sources.py` | 40 | 3 | 92% | ✅ |
| `lib/report_source.py` | 118 | 17 | 79% | ⚠️ just below 80% |
| `lib/youtube_playlist.py` | 28 | 3 | 83% | ✅ |
| `lib/deploy_app.py` | 190 | 16 | 87% | ✅ |
| `lib/ingest/__init__.py` | 7 | 0 | 100% | ✅ |
| `lib/ingest/agent_tools.py` | 83 | 23 | 66% | ⚠️ |
| `lib/ingest/aisearch.py` | 12 | 1 | 92% | ✅ |
| `lib/ingest/bundle.py` | 27 | 15 | 39% | 🔴 |
| `lib/ingest/compose.py` | 50 | 0 | 95% | ✅ (branch gaps) |
| `lib/ingest/dispatch.py` | 27 | 3 | 83% | ✅ |
| `lib/ingest/markdown.py` | 14 | 0 | 100% | ✅ |
| `lib/ingest/leaderboard.py` | 12 | 2 | 83% | ✅ |
| `lib/ingest/web.py` | 3 | 0 | 100% | ✅ |
| `lib/ingest/youtube.py` | 7 | 1 | 86% | ✅ |
| `lib/ingest/fixtures.py` | 13 | 2 | 76% | ⚠️ |
| `lib/ingest/lazy.py` | 93 | 25 | 67% | ⚠️ |
| `lib/ingest/topics/registry.py` | 27 | 0 | 100% | ✅ |
| `lib/ingest/topics/_preflight.py` | 38 | 14 | 57% | ⚠️ |
| `lib/ingest/topics/__init__.py` | 2 | 0 | 100% | ✅ |
| `lib/ingest/types.py` | 22 | 0 | 100% | ✅ |
| `lib/ingest/extractors/__init__.py` | 2 | 0 | 100% | ✅ |
| `lib/ingest/extractors/crawl.py` | 30 | 5 | 72% | ⚠️ |
| `lib/ingest/extractors/preflight.py` | 11 | 1 | 85% | ✅ |
| `lib/ingest/extractors/rss.py` | 97 | 33 | 61% | ⚠️ |
| `lib/ingest/extractors/structured.py` | 37 | 7 | 70% | ⚠️ |

---

## Comparison: Snapshot 2026-07-28 → 2026-07-29

| Module | Before | After | Delta |
|--------|-------:|------:|------:|
| `frame_author.py` | 73% | **91%** | +18% ✅ |
| `editorial.py` | 86% | **83%** | -3% ⚠️ (slight drift) |
| `history.py` | 92% | **90%** | -2% ⚠️ (slight drift) |
| `enrich.py` | 25% | **23%** | -2% 🔴 (regression) |
| `diagnostics.py` | 57% | **58%** | +1% ✅ |
| `environment.py` | 61% | **56%** | -5% 🔴 (regression) |
| **Overall core** | ~61% | **57%** | **-4% ⚠️** |

---

## Critical Gaps (blocking parity claims)

| Module | Cover | Concern |
|--------|------:|---------|
| `enrich.py` | **23%** | Core LLM enrichment — largely untested, highest regression risk |
| `llm_client.py` | **11%** | LLM client — untestable without live Ollama |
| `render.py` | **18%** | Report rendering — largely untested |
| `bundle.py` (lib) | **39%** | Ingest bundle logic — low coverage |

## Below 80% Threshold (need work before Track 3 parity claims)

| Module | Cover | Action |
|--------|------:|--------|
| `environment.py` | 56% | T1.6 fixture tests |
| `diagnostics.py` | 58% | T1.5 fixture tests |
| `doctor.py` | 77% | Add uncovered branch tests |
| `report_source.py` (lib) | 79% | Add missing branches |
| `frame_nav.py` | 68% | Add navigation tests |
| `validate.py` | 65% | Add validation edge cases |
| `agent_tools.py` (lib) | 66% | Add tool integration tests |
| `lazy.py` (lib) | 67% | Add lazy ingest tests |

## Already Green (≥80%)

- `config.py` (92%), `dates.py` (100%), `schema.py` (100%), `paths.py` (81%)
- `tools.py` (89%), `leaderboards.py` (86%), `structured_sources.py` (92%)
- `grounding.py` (84%), `editorial.py` (83%), `frame_author.py` (91%)
- `history.py` (90%), `site_footer.py` (91%), `visualize.py` (88%)

---

## Notes

- **Coverage failure triggered:** 57% < 80% fail-under threshold in pyproject.toml
- Admin/server modules (`admin_frame.py`, `admin_ops.py`, `admin_server.py`, `local_server.py`) excluded from parity scope — they're operational, not pipeline logic
- Shim files (`config.py`, `dates.py`, `schema.py`, `paths.py`, `leaderboards.py`, `structured_sources.py`, `tools.py` in llm_pipeline/) show 100% because they're thin deprecation wrappers
- HTML report available at: `htmlcov/index.html`
