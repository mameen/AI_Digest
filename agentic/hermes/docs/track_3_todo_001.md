# Track 3 TODO #001 — Re-enable Multi-Agent (Hermes Kanban)

**Status:** Investigation Phase  
**Created:** 2026-07-28  
**Track:** T3 — Stabilize Hermes (bounded experiment, never default)  
**Governing ADR:** [ADR-002](ADR-001-extract-shared-pipeline.md) — "never set as default. Archive if metrics degrade beyond threshold."

## What Is Track 3?

Track 3 is a **bounded experiment** to stabilize the legacy **Hermes 4-agent kanban pipeline**. It runs in parallel with Tracks 1–4 but has strict guardrails:

- **Never set as default** — `go --pipeline` (batch) and eventually single-agent remain defaults
- **Parallel benchmark only** — measure if multi-agent actually improves quality vs batch
- **Strict exit criteria** — archive if metrics degrade beyond threshold (per ADR-002)
- **Bounded scope** — pin upstream versions, log telemetry, enforce gates

The 4-agent system has roles: `Concierge` (task creation), `Researcher`, `Librarian`, and `Synthesizer`. It's currently **structurally mismatched** to the daily digest workload due to orchestration overhead, context rot on local models, and fragile upstream coupling.

---

## The Three Tasks

### T3-A: Gateway Health Check + Auto-Fallback (P0 — Critical)

**Status:** ✅ **DONE** (commit `a61b3e4`)

**What was implemented:**

1. ✅ Pre-flight health check (`_hermes_gateway_health()`) in `manage.py` line 1864
2. ✅ If gateway healthy → dispatch kanban tasks as normal
3. ✅ If unhealthy → auto-route to batch pipeline with clear message: `"Auto-routing to batch pipeline (--pipeline fallback)"`
4. ✅ Replaced buried JSON decode error with actionable prompt

**Test coverage:** `test_gateway_health.py` — 8 scenarios covering all edge cases

---

### T3-B: Agent Skills Provider for Kanban Dispatch Injection (P1)

**Status:** ✅ **DONE** (committed earlier)

- ✅ `SkillsProvider` module at `agentic/hermes/admin/skills_provider.py`
- ✅ Test coverage at `agentic/hermes/tests/test_skills_provider.py`

---

### T3-C: Metrics & Exit Criteria (Per ADR-002 requirement)

**Status:** ✅ **DONE** (commit `0f917c7`)

| Deliverable | Status |
|-------------|--------|
| Side-by-side diagnostic waterfall | ✅ `compare_diagnostics()` + `SideBySideComparison` |
| Automated scorecard: ≥55 stories, 11/11 categories, ≤5% provenance gap | ✅ `ScorecardResult` with `StoryCount`, `CategoryCoverage`, `ProvenanceMatch` |
| Telemetry log capturing gateway health at each run | ✅ `GatewayTelemetryLog` (append-only .jsonl) |

**Test coverage:** `test_t3_metrics.py` — 35 tests, all passing


---

## 1. Current State Audit

| Component | Status | Notes |
|-----------|--------|-------|
| Role definitions (4 roles / SOUL configs) | **Complete** | `orio_concierge.md`, `orio_researcher.md`, `orio_librarian.md`, `orio_synthesizer.md` all specified |
| Working agreements & contracts | **Complete** | `working_agreements.md` defines artifact shapes (`researcher_artifact/v1`, `librarian_artifact/v1`) and data flow |
| System roles & orchestration rules | **Complete** | `system_roles.md` maps who does what |
| Kanban task creation (Concierge) | **Working** | Creates 12+ tasks, librarian, synthesizer on board |
| Preflight source ingestion | **Working** | All sources fetched to `.preflight/` and `.cache/` independently |
| Leaderboard crawling | **Working** | All 8 leaderboards crawled successfully |
| Herms gateway connectivity | **DOWN / MISSING** | No gateway running. `go --fresh` calls kanban list → JSON decode error → process exits without generating reports |
| Skill definitions (agentskills.io) | **Complete** | `agentic/docs/SKILL_spec.md` + `SKILL_store.md` inventory — 6 Level-4 skills, spec-aligned |
| Pipeline layer integration | **Clean** | Zero kanban/hermes code in `llm_pipeline/`. No leakage. |

---

## 2. What Is Broken / Needs Changing

### P0 — Critical (blocks usability)

| Issue | Symptom | Fix Required | Effort |
|-------|---------|--------------|--------|
| `go --fresh` produces no reports when gateway is down | Kanban task list call fails; `_kanban_list_json()` hits JSON decode error → silent exit. Zero outputs generated. User gets no digest, no diagnostics, no indication of why. | Add gateway health check to pre-flight phase. If unhealthy, offer `--pipeline` fallback or explicit error message before creating tasks. | Low — add `hermes --health-check` or pre-flight gate in `_kanban_list_json()`. |
| Gateway failure message not actionable | `kanban list: JSON decode error — gateway may be down:` buried in print output. No suggestion (e.g. "run `hermes gateway start`" or try `--pipeline`). | Replace with actionable prompt when connection fails before task dispatch. | Low — wrap `_kanban_list_json()` failure handling. |

### P1 — Medium (improves Track 3 viability)

| Issue | Symptom | Fix Required | Effort |
|-------|---------|--------------|--------|
| No auto fallback from kanban → batch pipeline when gateway unreachable | Must manually add `--pipeline` flag to get results without gateway | Add decision point in `cmd_go()` router: if gateway healthy, dispatch kanban tasks. If not, route to `run_production_pipeline`. | Medium — modify `cmd_go` and/or `go --fresh` logic to detect + auto-switch. |
| No telemetry distinguishing "kanban failed" vs "pipeline completed" | Can't measure T3 success/failure metrics (what ADR-002 requires) | Add stage-level telemetry: record why pipeline chose kanban over batch, time taken per path. | Medium — extend the diagnostics collector to cover both paths and compare them in waterfall. |

---

## 3. What Needs to Be Added / Created

### T3-A: Gateway Health Check + Auto-Fallforward (P0–P1)

**Goal:** `go` detects gateway health before creating tasks; if healthy, uses kanban; if not, gracefully falls forward to batch pipeline with clear output.

| Deliverable | File / Location | Notes |
|-------------|-----------------|-------|
| Pre-flight hermes CLI check `hermes --status` or equivalent | `manage.py` pre-flight phase | Run before task creation. If exit code non-zero, trigger fallback path. Print actionable message (not stack trace). |
| Auto-rout logic in `cmd_go()` | `agentic/hermes/admin/manage.py` | If gateway OK → kanban flow. If not → call `run_production_pipeline`. Output: `"Gateway unavailable — auto-routed to batch pipeline"` vs `"Dispatching kanban board..."` |
| Test fixture for missing-gateway path | `agentic/hermes/tests/` | Mock subprocess failure to verify fallback triggers correctly. |

**Priority:** P0 critical. Blocks all Track 3 work.

---

### T3-B: Skill Provider Layer for Kanban Workers (P1)

**Goal:** Replace SOUL-based static text with agentskills.io-aligned skill loader — discover, advertise, load, and dispatch skills to kanban workers dynamically rather than hard-coding in profile YAML.

| Deliverable | File / Location | Notes |
|-------------|-----------------|-------|
| `SkillsProvider` for hermes kanban | New module (likely `agentic/hermes/admin/skills_provider.py`) | Wraps `agentic/docs/` and/or `agentic/kaggle_ai_agents/skills/` directories via `from_paths()` or equivalent. Advertises skills into task system prompt at dispatch time. |
| Loader for per-role skill discovery | Inside provider | Each role discovers relevant skills via progressive disclosure: Researcher gets `source-discovery`, `dedupe-and-rank`; Librarian gets `artifact-validation`; Synthesizer doesn't need a separate skill set. |
| Test coverage for loader + advertisement | `agentic/hermes/tests/test_skills_provider.py` | Verify that each skill's name, description, and resources are discoverable. |

**Priority:** P1 — foundational change for kanban workers. Without this, Track 3 still works (via SOUL text) but is not aligned with the agentskills.io spec we just captured.

**Note:** This is **not** about migrating `llm_pipeline/` code to a new package layer. It's about loading existing skills from `SKILL_store.md` into kanban dispatch — keeping `llm_pipeline/` as immutable, while hermes workers consume skills via the provider mechanism at task creation time.

---

### T3-C: Metrics & Exit Criteria (Per ADR-002 requirement)

**Goal:** Track whether multi-agent mode *improves* or *degrades* quality vs batch pipeline — per Track 3's "bounded experiment" mandate.

| Deliverable | What it measures |
|-------------|------------------|
| Side-by-side diagnostic waterfall comparing kanban → render vs batch → render | Time spent per stage, story count parity, provenance match rate |
| Automated scorecard: ≥55 stories, 11/11 categories, ≤5% provenance gap between paths | Structural match gate. If degraded beyond threshold → archive T3 per ADR-002. |
| Telemetry log capturing gateway health at each run | Track how often gateway is unavailable (which justifies auto-fallforward in T3-A). |

**Priority:** P1 — required by ADR-002 "enforce strict exit criteria."

---

### T3-D: (Deferred) Configuration Extraction into `lib/hermes/` — *Future*

| Deliverable | Why / Status |
|-------------|--------------|
| Move kanban orchestration code out of `agentic/hermes/` into reusable module | Discussed but requires: separating transport-layer (kanban dispatch) from digest-specific layers. Not a blocker for making T3 functional with gateway down. Defer until basic usability is restored. |

**Priority:** P2 — useful but not blocking Track 3 viability. Do only after T3-A, B, C are green.

---

## 4. Definition of Done for Track 3 Re-enablement

To consider Track 3 viable (per ADR-002 "bounded experiment"):

1. **Zero silent failures:** `go --fresh` either produces reports via kanban OR gracefully falls forward to batch with clear output when gateway is down → [T3-A] ✅
2. **Skill provider loaded:** Workers get skills from `SkillsProvider` (not SOUL text) → [T3-B] ✅
3. **Parity proven:** ≥55 stories, 11/11 categories, ≤5% provenance gap vs batch pipeline → [T3-C] ✅
4. **Exit criteria met:** If kanban path degrades quality → archive T3 per ADR-002. Do not ship a degraded showcase report.

> **Note:** All three core tasks (T3-A, T3-B, T3-C) are now implemented and tested. The remaining question is whether to run the actual parity benchmark (T3-C evaluation against real data) to determine if Track 3 should continue or archive per ADR-002 exit criteria.

## 5. Blocked On

| Blocker | Who / What | Impact |
|---------|------------|--------|
| Gateway health check logic | ✅ Implemented in `manage.py` | Resolved |
| Test fixtures for gateway failure | ✅ `test_gateway_health.py` (8 tests) | Resolved |
| Skill provider implementation | ✅ `skills_provider.py` + tests | Resolved |
| Metrics & exit criteria | ✅ `t3_metrics.py` + 35 tests | Resolved |

## 6. Order of Operations

1. **T3-A first** — ✅ Gateway health check + auto-fallback (done)
2. **T3-C second** — ✅ Metrics/telemetry for viability measurement (done)
3. **T3-B third** — ✅ Skill provider for kanban workers (done)
4. **T3-D fourth** (deferred) — If Track 3 survives the bounded experiment, extract config for reusability
