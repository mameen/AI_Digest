# ADR-002: Pivot from Multi-Agent Kanban to Single-Agent-with-Skills Runtime & Strict Hermes Isolation

**Status:** Proposed / Updating  
**Date:** 2026-07-28 (Updated 2026-07-29)  
**Supersedes:** Unbounded Hermes crew iterations and cross-pipeline fallback mechanisms  

---

## Context

AI Digest operates two main execution paradigms:
1. **Batch Pipeline (`llm_pipeline/`):** The legacy batch driver (`ingest → enrich → validate → render`).
2. **Hermes Multi-Agent (`agentic/hermes/`):** The 4-role Kanban crew (`Concierge`, `Researcher`, `Librarian`, `Synthesizer`).

The multi-agent Hermes Kanban setup is structurally mismatched to a bounded daily digest workload on local compute, facing orchestration overhead, context degradation on smaller models, and fragile upstream coupling. 

To safely evaluate and migrate the architecture, the project enforces a strict separation between shared domain utilities (`./lib`), Hermes-specific adapters (`./lib/hermes`), and individual runtime drivers (`llm_pipeline/` and `agentic/hermes/`).

---

## Architectural Invariants & Boundary Rules

### 1. Zero Cross-Pipeline Coupling & No Auto-Fallbacks
- **Self-Sufficiency:** `agentic/hermes/` must operate as a standalone, self-sufficient execution environment.
- **No Import Inversion:** `agentic/hermes/` (including `admin/manage.py`) must **NEVER** import from `llm_pipeline/` (e.g., `run_production_pipeline`).
- **Fail Hard Policy:** If the Hermes Gateway is down, unreachable, or encounters an internal protocol violation during a Track 3 run (`manage.py go --fresh`), execution must **fail immediately with a non-zero exit code** and clear stack trace. It must **not** silently fall back or forward into `llm_pipeline/`.

### 2. Dependency Hierarchy

```mermaid
graph TD
    subgraph Shared Domain Utilities
        LIB["./lib<br>(Domain Tools & Schemas)"]
    subgraph Hermes Adapters
        LIB_HERMES["./lib/hermes<br>(Skills & Gateway Adapters)"]
    subgraph Runtime Drivers
        LLM_PIPE["llm_pipeline<br>(Batch Pipeline Driver)"]
        HERMES_RUN["agentic/hermes<br>(Hermes Kanban CLI/Runner)"]

    LIB --> LLM_PIPE
    LIB --> LIB_HERMES
    LIB --> HERMES_RUN
    LIB_HERMES --> HERMES_RUN

    %% Enforced Boundaries
    HERMES_RUN -.-x|FORBIDDEN IMPORT / FALLBACK| LLM_PIPE
    LLM_PIPE -.-x|FORBIDDEN IMPORT| LIB_HERMES

```

1. **`./lib/`**: Generic, headless domain logic (source ingestion, grounding, validation, schemas, rendering).
2. **`./lib/hermes/`**: Hermes-specific adapters, skills providers (`skills_provider.py`), gateway protocol client interfaces, and card converters. It consumes `./lib/` but has **zero knowledge** of `llm_pipeline/`.
3. **`agentic/hermes/`**: The Hermes CLI and Kanban board runner (`manage.py`). It imports exclusively from `./lib/hermes/` and `./lib/`.
4. **`llm_pipeline/`**: The batch execution driver. It imports exclusively from `./lib/`.

---

## Strategy & Four-Track Execution Plan

To systematically resolve multi-agent debt while preserving production stability, work is organized across four parallel tracks:

| Track | Name | Objective | Governance Rule |
| --- | --- | --- | --- |
| **Track 1** | **Fortify Baseline (`llm_pipeline`)** | Increase test coverage (≥80%) across shared primitives in `./lib/` and `llm_pipeline/`. | Maintains stable production fallback via `manage.py go --pipeline`. |
| **Track 2** | **Extract Shared Primitives (`./lib`)** | Decouple pure python domain tools (ingest, ground, validate, render) into `./lib`. | Shared zero-side-effect utilities usable by any runtime. |
| **Track 3** | **Stabilize & Benchmark Hermes (`agentic/hermes`)** | Clean up Hermes orchestration using `./lib/hermes`, enforce explicit error handling, and test with upgraded models (`qwen3.6:35b`). | **Bounded experiment.** Hard-fails on gateway outage. Never set as default runtime. |
| **Track 4** | **Single-Agent-with-Skills Runtime** | Implement efficient single-agent runtime with progressive disclosure (`SKILL.md`) aligned with `agentskills.io`. | Target runtime for production once parity is reached. |

---

## Decision Criteria & Parity Gates for Track 3

Track 3 (Hermes Multi-Agent) is maintained as a bounded benchmark with strict exit criteria:

1. **Explicit Failures:** Gateway unreachability or socket connection failures raise a hard `RuntimeError` during pre-flight checks (`manage.py go --fresh`).
2. **Metrics Threshold:** Track 3 must demonstrate parity against the baseline pipeline:
* Total Stories Processed: $\ge 55$
* Category Coverage: $11 / 11$ categories represented
* Provenance Gap: $\le 5\%$ gap vs batch baseline


3. **Sunset / Archive Rule:** If Track 3 fails to meet parity without excessive orchestration overhead or requires cross-pipeline crutches, `agentic/hermes/` will be formally archived to reference status without affecting core product execution.

---

## Consequences

### Positive

* **Architectural Clarity:** Clean physical and logical separation of concerns between drivers and shared library code.
* **Accurate Telemetry & Diagnostics:** Hard failures on gateway issues prevent false-positive green runs and surface real Hermes protocol/network bugs immediately.
* **Decoupled Maintenance:** Changes to `llm_pipeline/` cannot break `agentic/hermes/` and vice versa.

### Negative / Technical Debt

* **No Automatic Safety Net during T3 Testing:** Running Track 3 explicitly requires an active, healthy Hermes gateway; failures will abort execution rather than outputting a fallback report.
