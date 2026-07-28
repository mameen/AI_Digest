# ADR-002: Pivot from Multi-Agent Kanban to Single-Agent-with-Skills Runtime

**Status:** Proposal  
**Date:** 2026-07-28  
**Supersedes:** Aggressive Hermes crew iterations and parallel kanban stabilization attempts

---

## Context

AI Digest operates two pipelines sharing the deterministic tail `llm_pipeline/` (`ingest → enrich → validate → render`). The legacy batch pipeline (`go --pipeline`) remains reliable. In contrast, the labeled "production" **Hermes kanban crew** (4-role architecture) is structurally mismatched to a bounded daily digest workload. Multi-agent coordination overhead now exceeds throughput benefits, compounded by local compute constraints and fragile upstream coupling. This pivot adopts a four-track parallel strategy to safely migrate to a single-agent-with-skills runtime while preserving production stability.

See [Issue 001](./issue_001.md)

### Current Deficiencies
1. **Orchestration Tax:** Four roles × kanban transitions create sync complexity, prompt chain drift, and retry cascades baked into the Hermes dispatcher (`protocol_violation`, `stale`, `reclaimed`).
2. **Context Rot & Local Throttling:** Librarian fan-in overwhelms local context windows (`llama3.1` on Ollama), triggering "lost in the middle" degradation. Parallelism is artificially capped (`kanban.max_in_progress 1`), negating multi-agent speed advantages.
3. **Upstream Coupling:** Requires 8 `site-packages` patches to bridge missing native hooks for custom goal loops, toolsets, and artifact validation gates. Uncontrolled `pip upgrade` silently breaks production.
4. **Architectural Mismatch:** Research confirms single-agent + skill libraries cut latency ~50% and token usage ~54% for deterministic workflows. Multi-agent only wins when context utilization degrades—a condition ORIO’s pipeline actively avoids.

---

## Verified System Constraints

1. **Dispatcher TTLs & Heartbeats Are Hard Limits:** Hermes enforces strict claim TTLs and liveness probes. Mismatches cause cascading stalls that are framework-level, not ORIO code quality issues.
2. **Librarian Fan-In Bloat Is Inevitable:** Raw researcher outputs converge into a single context window regardless of orchestration wrapper. Local models cap effective utilization before aggregation completes.
3. **Code-Level Artifact Gates Are Non-Negotiable:** Prompt-only validation allows truncated or hallucinated digests to pass kanban state transitions. Structural gates must remain in `llm_pipeline/`.
4. **Local Compute Has Zero Margin for Overhead:** Ollama runs without cloud redundancy. Any architectural shift must preserve deterministic timing and bounded memory profiles.

---

## Decision

We adopt a **Four-Track Parallel Strategy**: Fortify the batch fallback, Extract/Package shared libs, Stabilize Hermes as a bounded experiment, and Build the single-agent-with-skills runtime as the production default. Tracks operate in parallel with strict parity gates before any sunset.

### Track 1: Fortify `llm_pipeline/`
Lock the batch pipeline as the fallback of record. Maintain `go --pipeline` green state **and enforce baseline test/fixture coverage on all deterministic tail modules before extracting any shared code**. Zero removals until single-agent parity is proven via automated fixtures.

### Track 2: Extract & Package Shared Libs
Convert `llm_pipeline` + `lib` into formal importable packages via `pyproject.toml`. Eliminate `sys.path.insert` hacks. Retire the 8 Hermes patches incrementally as they become obsolete.

### Track 3: Stabilize (Hermes 4-Agent)
Run parallel benchmark only. Pin upstream version, log orchestration telemetry, and enforce strict exit criteria. Never set as default. Archive if metrics degrade beyond threshold.

### Track 4: Build Single-Agent-with-Skills
Implement progressive skill discovery, file-based state routing (`preflight/`, `.cache/`), and deterministic tail calls to `llm_pipeline.validate_and_render()`. Hierarchical routing prevents selection degradation as scope grows.

---

## Detailed Implementation Plan

### Phase 1: Package Governance & Import Hardening
Create `/pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "orio-digest"
version = "0.7.0"
dependencies = ["instructor>=2.0", "pydantic>=2.10", "pyyaml>=6.0", "jinja2>=3.1"]

[tool.setuptools.packages.find]
where = ["."]
include = ["llm_pipeline*", "lib*", "agentic/single_hermes_agent*"]
```
Establish regression fixtures covering the full fallback path (ingest → enrich → validate → render). Verify clean venv sync across worker profiles before removing dynamic import fallbacks.

### Phase 2: Single-Agent Skill Scaffolding
```
agentic/single_hermes_agent/skills/
├── feed_ingestion/          # Fetch, parse, crawl — deterministic scripts
│   └── SKILL.md
├── story_curation/          # Classify, dedupe, score, map to topics
│   └── SKILL.md
└── digest_synthesis/        # Generate prose, JSON schema output
    └── SKILL.md
```
Skills load metadata only (~100 tokens). Full `SKILL.md` activates on trigger. State routes via filesystem, not conversation history.

### Phase 3: Parity & Feature Flag Switch
- Run A/B validation: `single_hermes_agent` vs `go --pipeline`. Target: ≥55 stories, 11/11 categories, structural match.
- Ship feature flag: `manage.py go` defaults to single-agent. Keep `--hermes-crew` for legacy fallback.

### Phase 4: Sunset & Archive
Move `agentic/hermes/` to reference/archive. Sunset patches. Fully migrate imports to package namespace.

---

## Consequences

### Positive
- **Eliminated Coordination Overhead:** Single context window, no kanban handoff latency, zero protocol violations.
- **Deterministic Tail Preservation:** `grounding.py`, `validate.py`, `render.py` remain unchanged and callable by the new runtime.
- **Research-Aligned Efficiency:** ~50% lower latency, ~54% fewer tokens for bounded daily workflows.
- **Clean Import Chain:** Formal packaging removes `sys.path` hacks and patch-dependent bootstraps.

### Negative / Technical Debt
- **Parallel Maintenance Cost:** Hermes telemetry logging and exit-criteria tracking require dedicated CI checks during transition.
- **Upfront Skill Design Overhead:** Metadata schemas, hierarchical routing rules, and progressive disclosure gates must be specified before sprint work.
- **Feature-Flag Governance:** Dual-path execution requires strict observability hooks to catch drift between pipelines before full switch.
- **Long-Term Resolution:** True multi-agent flexibility requires contributing dynamic toolset registration and custom kanban gates to Hermes Core (tracked in [ADR-003](./adr-hermes-plugin-architecture.md)).