# llm_pipeline/ — Module Governance & Refactoring Plan

**Status:** Active  
**Date:** 2026-07-27  
**Supersedes:** None — this is the module-level companion to `.agents/AGENTS.md`

---

## Mandate

Per [ADR-002](../agentic/hermes/docs/ADR-001-extract-shared-pipeline.md), `llm_pipeline/` is the **immutable floor**: the parity benchmark and safety net for Track 1. Zero removals, zero regressions until the single-agent runtime proves parity via automated fixtures.

---

## Refactoring Goal: Extract Reusable Code into `lib/`

### Objective

Move deterministic, reusable utilities from `llm_pipeline/` into `lib/` as formal importable packages — eliminating `sys.path.insert` hacks and enabling clean imports for both the batch pipeline and the future single-agent runtime.

### Scope

| Category | Modules to evaluate for extraction |
|---|---|
| **Path constants** | `llm_pipeline/paths.py` → `lib/paths.py` (already exists; align) |
| **Schema / types** | `llm_pipeline/schema.py` → `lib/schema.py` |
| **Config loading** | `llm_pipeline/config.py` → `lib/config.py` |
| **Date utilities** | `llm_pipeline/dates.py` → `lib/dates.py` |
| **Leaderboard sources** | `llm_pipeline/structured_sources.py` → `lib/leaderboards.py` |
| **Link extraction** | `llm_pipeline/vendor/ai-news-digest/scripts/link_extract.py` → `lib/link_extract.py` |
| **Cache utilities** | `llm_pipeline/vendor/ai-news-digest/scripts/_cache_utils.py` → `lib/cache_utils.py` |
| **Story utilities** | `llm_pipeline/vendor/ai-news-digest/scripts/_story_utils.py` → `lib/story_utils.py` |

### Extraction Rules

1. **Never delete from `llm_pipeline/` first.** Move → verify tests pass → deprecate old import with a `DeprecationWarning` → remove in a future release.
2. **Every moved module must retain its existing public API.** No breaking changes to function signatures, class interfaces, or return types.
3. **Tests move with the code.** Each extracted module gets its test file in `lib/tests/` (or reuses an existing one from `llm_pipeline/tests/`).
4. **Coverage parity required.** After extraction, coverage for the moved module must be ≥ its current baseline (see Snapshot 1 below). No regression allowed.
5. **`lib/__init__.py` becomes the public namespace.** Re-export extracted modules so consumers can do `from lib import schema, config, dates`.

---

## Coverage Baseline (Snapshot 1 — 2026-07-27)

Measured via `coverage run -m unittest discover -s llm_pipeline/tests`.

### Modules Targeted for Extraction

| Module | Stmts | Miss | Cover | Extraction Priority |
|---|---:|---:|---:|---:|
| `llm_pipeline/schema.py` | 65 | 0 | **100%** | P0 — already perfect |
| `llm_pipeline/config.py` | 27 | 2 | **93%** | P0 — trivial gaps |
| `llm_pipeline/paths.py` | 38 | 8 | **79%** | P0 — align with `lib/paths.py` |
| `llm_pipeline/dates.py` | 39 | 20 | **49%** | P1 — needs more tests first |
| `llm_pipeline/structured_sources.py` | 51 | 6 | **88%** | P1 |
| `llm_pipeline/leaderboards.py` | 139 | 17 | **88%** | P1 |
| `llm_pipeline/tools.py` | 185 | 24 | **87%** | P1 |
| `llm_pipeline/grounding.py` | 114 | 12 | **89%** | P2 — core, keep in pipeline |
| `llm_pipeline/vendor/.../link_extract.py` | 170 | 144 | **15%** | P2 — needs tests before extract |
| `llm_pipeline/vendor/.../_cache_utils.py` | 44 | 31 | **30%** | P2 |
| `llm_pipeline/vendor/.../_story_utils.py` | 24 | 16 | **33%** | P2 |

### Modules NOT to Extract (keep in pipeline)

| Module | Cover | Reason |
|---|---:|---|
| `enrich.py` | 19% | Core LLM enrichment — highest regression risk, needs tests first |
| `editorial.py` | 36% | Editorial brief assembly — pipeline-specific logic |
| `diagnostics.py` | 57% | Large (413 stmts), admin UI coupled |
| `doctor.py` | 83% | Admin CLI tool |
| `frame_author.py` | 17% | Frame generation — pipeline-specific |
| `history.py` | 23% | History tracking — pipeline-specific |
| `render.py` | — | Render stage — deterministic tail, keep as-is |
| `validate.py` | — | Validation gate — deterministic tail, keep as-is |

---

## Refactoring Workflow (Per Module)

For each module to extract:

1. **Add tests** in `llm_pipeline/tests/` if coverage < 80% (use real fixtures, no mocks).
2. **Create the file** in `lib/` with identical public API.
3. **Update `lib/__init__.py`** to re-export the module.
4. **Add deprecation shim** in `llm_pipeline/` that imports from `lib` and emits `DeprecationWarning`.
5. **Run full test suite**: `python run_tests.py` — must pass 100%.
6. **Run coverage**: verify no regression from baseline.
7. **Commit** the change on a branch, ask permission before push.

---

## Parity Gate

No module may be fully removed from `llm_pipeline/` until:

1. All tests in `llm_pipeline/tests/` pass against the deprecation shim.
2. Coverage for the moved module is ≥ baseline snapshot.
3. The single-agent runtime (Track 4) imports from `lib/` and achieves parity vs `go --pipeline`.

---

## References

- [ADR-002](../agentic/hermes/docs/ADR-001-extract-shared-pipeline.md) — Four-track pivot strategy
- [Track 1 TODO #001](../agentic/hermes/docs/track_1_todo_001.md) — Coverage action items
- [.agents/AGENTS.md](../../.agents/AGENTS.md) — Repo-wide agent rules
