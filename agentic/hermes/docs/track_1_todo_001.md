# Track 1: Fortify `llm_pipeline/` — Parity Benchmark & Safety Net

**Status:** Active  
**Date:** 2026-07-27  
**Supersedes:** None — this is the baseline guardrail for ADR-002

---

## Mandate

Track 1 is the **immutable floor**: `llm_pipeline/` is locked as the parity benchmark and safety net. Zero removals, zero regressions on that code until the single-agent runtime proves it out in automated fixtures.

---

## Snapshot 1: Code Coverage Baseline (2026-07-27)

Measured via `coverage run -m unittest discover -s llm_pipeline/tests`.

### Core Pipeline Modules

| Module | Stmts | Miss | Cover |
|---|---:|---:|---:|
| `llm_pipeline/__init__.py` | 3 | 0 | 100% |
| `llm_pipeline/config.py` | 27 | 2 | 93% |
| `llm_pipeline/dates.py` | 39 | 20 | 49% |
| `llm_pipeline/diagnostics.py` | 413 | 176 | 57% |
| `llm_pipeline/doctor.py` | 142 | 24 | 83% |
| `llm_pipeline/editorial.py` | 152 | 98 | 36% |
| `llm_pipeline/enrich.py` | 320 | 259 | 19% |
| `llm_pipeline/environment.py` | 181 | 70 | 61% |
| `llm_pipeline/frame_author.py` | 60 | 50 | 17% |
| `llm_pipeline/grounding.py` | 114 | 12 | 89% |
| `llm_pipeline/history.py` | 48 | 37 | 23% |
| `llm_pipeline/leaderboards.py` | 139 | 17 | 88% |
| `llm_pipeline/paths.py` | 38 | 8 | 79% |
| `llm_pipeline/schema.py` | 65 | 0 | 100% |
| `llm_pipeline/site_footer.py` | 26 | 8 | 69% |
| `llm_pipeline/structured_sources.py` | 51 | 6 | 88% |
| `llm_pipeline/styles.py` | 25 | 5 | 80% |
| `llm_pipeline/tools.py` | 185 | 24 | 87% |
| **pipeline/__init__.py** | 2 | 0 | 100% |
| **TOTAL (core)** | **~2,330** | **~914** | **~61%** |

### Test Files (already well-covered)

| Module | Stmts | Miss | Cover |
|---|---:|---:|---:|
| `tests/test_carry_forward.py` | 82 | 3 | 96% |
| `tests/test_diagnostics.py` | 121 | 1 | 99% |
| `tests/test_doctor.py` | 86 | 1 | 99% |
| `tests/test_environment.py` | 64 | 1 | 98% |
| `tests/test_grounding.py` | 100 | 1 | 99% |
| `tests/test_leaderboards.py` | 109 | 1 | 99% |
| `tests/test_structured_sources.py` | 56 | 1 | 98% |
| `tests/test_tools.py` | 154 | 1 | 99% |
| `tests/test_version.py` | 34 | 1 | 97% |
| `tests/test_video_chapters.py` | 114 | 1 | 99% |

### Critical Gaps (risk to parity)

| Module | Cover | Concern |
|---|---:|---|
| `enrich.py` | **19%** | Core LLM enrichment — largely untested, highest regression risk |
| `frame_author.py` | **17%** | Frame generation — untested |
| `editorial.py` | **36%** | Editorial brief assembly — low coverage |
| `history.py` | **23%** | History tracking — low coverage |
| `diagnostics.py` | 57% | Large file (413 stmts), half uncovered |
| `environment.py` | 61% | Config/environment handling |

---

## Action Items

- [ ] **T1.1** Raise `enrich.py` coverage from 19% → ≥80% before any Track 2/3/4 parity claims
- [ ] **T1.2** Raise `frame_author.py` coverage from 17% → ≥80%
- [ ] **T1.3** Raise `editorial.py` coverage from 36% → ≥80%
- [ ] **T1.4** Raise `history.py` coverage from 23% → ≥80%
- [ ] **T1.5** Add fixture-backed tests for `diagnostics.py` uncovered branches (lines 48-51, 55, 60-63, 72, 126, 175, 244-252, 288, 301-303, 314-316, 384-403, 408-427, 432-456, 460-462, 490-533, 543-544, 554-566, 570-588, 593-610, 621-636, 641, 643, 659-665, 690-703, 719, 855-859)
- [ ] **T1.6** Add fixture-backed tests for `environment.py` uncovered branches (lines 61, 78, 150-168, 173, 182-183, 185, 193-198, 200-207, 214-216, 230, 238-239, 244-256, 263-267, 276-281, 316, 320-321)
- [ ] **T1.7** Establish a CI gate: `llm_pipeline/` core coverage must stay ≥ baseline (61%) — no regression allowed
- [ ] **T1.8** After each parity claim from Track 4, re-run this snapshot and compare against this baseline

---

---

## Track 2 Extraction Progress (Snapshot 2026-07-28)

Per ADR-002 Phase 1, the following modules have been extracted to `lib/` with deprecation shims in place:

| Extracted Module | Canonical Location | Shim Location | Status |
|---|---|---|---|
| `config.py` (Config, load_config, _apply_llm_defaults, _default_llm) | `lib/config.py` | `llm_pipeline/config.py` | ✅ Shim active (DeprecationWarning) |
| `schema.py` (Story, Category, DigestDocument, etc.) | `lib/schema.py` | `llm_pipeline/schema.py` | ✅ Shim active (DeprecationWarning) |
| `paths.py` (REPO_ROOT, LLM_PIPELINE_ROOT, WEB_ROOT, AGENTIC_ROOT) | `lib/paths.py` | — | Already in lib/ |

### Public namespace (`lib/__init__.py`)

```python
from lib.config import Config, load_config
from lib.paths import REPO_ROOT, LLM_PIPELINE_ROOT, WEB_ROOT, AGENTIC_ROOT
from lib.schema import Story, Category, DigestDocument, ResourceLink
```

### E2E Verification (2026-07-28)

Pipeline run: `python run.py --start 2026-07-28` — **GREEN**

- All 4 phases completed without errors
- 106 total stories across 12 categories
- Deprecation shims working (warnings emitted, no breakage)
- Validation passed, reports rendered correctly

### Remaining Work

- [ ] Update remaining `llm_pipeline/` imports to use `lib.*` directly (eliminate shim warnings)
- [ ] Create `pyproject.toml` for formal package governance
- [ ] Retire Hermes patches incrementally as they become obsolete
- [ ] Remove deprecation shims once single-agent parity is proven

---

## Parity Gate Rule

No module in `llm_pipeline/` may be removed, deprecated, or have its public API changed until:

1. The single-agent runtime achieves ≥55 stories, 11/11 categories, structural match vs `go --pipeline`
2. All T1.x action items are complete
3. A new coverage snapshot shows no regression from this baseline
4. Track 2 extraction is verified via E2E pipeline run (see above)
