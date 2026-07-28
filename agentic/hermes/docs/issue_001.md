# ORIO Architecture Pivot: Problem, Constraints & 4-Track Strategy

## 🔍 Core Problem Summary
ORIO runs two pipelines sharing the deterministic tail `llm_pipeline/` (`ingest → enrich → validate → render`). The legacy batch pipeline (`go --pipeline`) is reliable and stable. In contrast, the labeled "production" **Hermes kanban crew** (4-agent architecture) is structurally mismatched to the workload. It suffers from orchestration overhead, fragile state handoffs, and context bloat for a bounded, deterministic daily digest. This is not a code quality issue—it is an architectural ceiling where multi-agent coordination costs outweigh their benefits for this specific use case.

## 🚧 Key Constraints & Architectural Limits
- **Orchestration Tax:** Four roles × kanban transitions create sync complexity, prompt chain drift, and repeated failure points per cycle.
- **Dispatcher Fragility:** Hermes enforces strict TTLs, heartbeats, and retry limits (`protocol_violation`, `stale`, `reclaimed`). Mismatches cause cascading stalls that are baked into the framework, not ORIO code.
- **Context Rot:** The Librarian fan-in step overwhelms local context windows (e.g., `llama3.1` on Ollama), triggering "lost in the middle" degradation and hallucination drift.
- **Upstream Coupling:** Requires 8 `site-packages` patches to bridge missing native hooks for custom goals, toolsets, and validation gates. Any `pip upgrade` silently breaks production.
- **Local Compute Limits:** Running on Ollama without cloud redundancy forces strict concurrency caps (`kanban.max_in_progress 1`). Multi-agent parallelism is artificially throttled, negating its speed advantages.
- **Research-Backed Reality:** Recent studies confirm single-agent + skill libraries cut latency by ~50% and token usage by ~54% for deterministic workflows. Multi-agent only wins when context utilization breaks down—a condition ORIO’s pipeline actively avoids.

## 🗺️ The 4-Track Migration Strategy
| Track | Objective | Scope & Guardrails |
|-------|-----------|-------------------|
| **1. Fortify** | Lock `llm_pipeline/` as the fallback & safety net. | Keep `go --pipeline` green at all times. Zero removals until single-agent parity is proven. This is insurance, not a stepping stone. |
| **2. Extract** | Package shared libs & retire upstream patches. | Complete `pyproject.toml` packaging for `llm_pipeline` + `lib`. Eliminate `sys.path` hacks. Document/retire the 8 Hermes patches as they become obsolete. |
| **3. Stabilize (Hermes 4-Agent)** | Run parallel benchmark, not production dependency. | Pin Hermes version. Log orchestration tax (handoff latency, retries, context bloat). Set strict exit criteria: archive if single-agent meets parity with <50% token cost. Never set as default. |
| **4. Build (Single-Agent-with-Skills)** | Ship the efficient production path. | Progressive disclosure (~100t skill metadata), file-based state routing (`.preflight/`, `.cache/`), and deterministic tail calls to `validate_and_render()`. Hierarchical skill selection prevents degradation as scope grows. |

## ⏱️ Execution Sequence
1. **Package & Lock:** Ship `pyproject.toml` + worker venv sync. Run `run_tests.py` green.
2. **Scaffold Skills:** Implement `feed_ingestion`, `story_curation`, `digest_synthesis` with `SKILL.md`. Verify sequential runner loads correctly.
3. **A/B Parity Test:** Compare `single_hermes_agent` output vs `go --pipeline`. Target: ≥55 stories, 11/11 categories, structural match.
4. **Feature Flag Switch:** Default to single-agent via `manage.py go`. Keep `--hermes-crew` flag for legacy fallback.
5. **Archive & Retire:** Move `agentic/hermes/` to reference/archive. Sunset patches. Fully migrate imports.

## ✅ Bottom Line
Stop patching a multi-agent framework that lacks native support for your bounded workflow. The research, upstream limitations, and local constraints all point to the same conclusion: **accelerate the single-agent-with-skills track** while keeping `llm_pipeline/` as your fortified fallback. Build beside it, prove parity, then flip the default.
