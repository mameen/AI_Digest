# Track 3 Issue #0001: Agent Architecture Debate & Mitigation Analysis

**Track:** T3 — Hermes Multi-Agent Kanban  
**Created:** 2026-07-28  
**Updated:** 2026-07-29  
**Status:** Under Active Evaluation  
**Governing ADR:** [ADR-002](ADR-001-extract-shared-pipeline.md)  

---

## 1. Executive Summary

A deep architectural debate occurred regarding the viability of the **Hermes 4-agent Kanban crew** (`Concierge`, `Researcher`, `Librarian`, `Synthesizer`) versus pivoting directly to **Track 4 (Single-Agent with Skills)**.

Code Assistant 3 argued that multi-agent orchestration under local compute constraints imposes a severe "orchestration tax" without speed or throughput benefits. The counter-argument established that Kanban and distributed DAG coordination are essential primitives for decoupling, provenance, and multi-machine scaling.

This document formalizes every issue raised by Assistant 3, the technical rebuttals, the hardware/model mitigations (`qwen3.6:35b`), and the strict boundary rules governing Track 3.

---

## 2. Evaluation of Kanban Architecture for ORIO

Kanban is a proven coordination pattern, but its cost-to-benefit ratio must be evaluated specifically against ORIO's bounded daily digest workload.

### Pros of Kanban in ORIO
* **Decoupling:** Roles do not depend on each other's internal logic, maintaining a clean separation of concerns.
* **Visibility & Inspection:** Board state is inspectable at any point during execution, enabling precise debugging and execution tracing.
* **Retry Resilience:** Failed or stalled tasks can be reclaimed and retried independently without restarting the whole pipeline.
* **Provenance:** Each `Researcher` reflects and grounds its own artifact, ensuring downstream roles receive trusted inputs.

### Cons & Deficiencies (Under Local Compute Constraints)
* **Orchestration Tax:** Running 4 roles across Kanban state transitions introduces sync complexity, prompt chain drift, serialization overhead, and retry cascades (`protocol_violation`, `stale`, `reclaimed`).
* **Context Rot & "Lost in the Middle":** Fan-in at the `Librarian` step overwhelms local model context windows (e.g., `llama3.1` on Ollama), leading to summary degradation and missing tail facts.
* **Artificial Parallelism:** Local single-GPU setups forced `kanban.max_in_progress: 1`, turning the system into sequential agent handoffs with expensive state serialization in between.
* **Upstream Coupling:** Operating Hermes required 8 local `site-packages` patches to bridge missing native framework hooks for custom goal loops and validation gates.
* **Dispatcher Fragility:** Strict framework-level TTLs, heartbeats, and timeouts cause cascading stalls when local model generation runs slow.

---

## 3. Comprehensive Debate & Point-by-Point Rebuttals

### Issue 1: "Artificial Parallelism" & `kanban.max_in_progress: 1`
* **Assistant 3's Position:** Because local GPU/Ollama hardware forces `kanban.max_in_progress: 1`, Kanban isn't actually running tasks in parallel. It is merely running sequential agent handoffs with state serialization overhead, giving zero speed advantage over a simple loop.
* **Architectural Rebuttal:** `kanban.max_in_progress: 1` was a temporary local testing cap, not a structural limit. While LLM generation relies on the GPU, CPU resources are free to perform async network fetching, feed parsing, graph coordination, and board state transitions concurrently.
* **Resolution / Fix:**
  1. Concurrency is decoupled from LLM inference using an **Async Waterfall DAG**.
  2. The `Concierge` constructs a Graph ID with dependent task nodes ($S$ sources, $C$ categories).
  3. `Researchers` run I/O-bound web fetching concurrently on the CPU, using semaphores to trigger downstream tasks automatically upon completion.

---

### Issue 2: Context Rot & "Lost in the Middle" Degradation
* **Assistant 3's Position:** Aggregating raw research from multiple `Researcher` tasks into the single `Librarian` role causes context bloat on local models like `llama3.1`. The model loses key details in the middle of long prompts and produces hallucinated or incomplete summaries.
* **Architectural Rebuttal:** Context bloat is caused by weak outputs from `Researchers` pushing unformatted, noisy text downstream, combined with undersized context models. Strict contractual boundaries and better models eliminate this failure mode.
* **Resolution / Fix:**
  1. **Model Upgrade:** Upgrading local model execution across all roles from `llama3.1` to **`qwen3.6:35b`**.
  2. **Contract Enforcement:**
     * **Researcher Output Contract:** Must output a clean, well-formed Markdown card with validated URLs.
     * **Librarian Feedback Loop:** If a `Researcher` card is poorly formed or noisy, the `Librarian` captures this inefficiency and provides direct feedback or rejects the task card.
     * **Synthesizer Input Contract:** The `Librarian` transforms verified cards into well-formed JSON for the `Synthesizer`, ensuring zero context bloat during report generation.

---

### Issue 3: Dispatcher Fragility (TTLs, Heartbeats, Cascading Stalls)
* **Assistant 3's Position:** Strict framework-level TTLs, claim timeouts, and heartbeat checks in Hermes cause cascading stalls and protocol violations when local inference is slow. These failures are baked into the dispatcher and cannot be cleanly caught in ORIO application code.
* **Architectural Rebuttal:** TTLs, heartbeats, and claim timeouts are essential engineering primitives for any system intended to scale horizontally across multiple machines in the future. Removing them creates silent deadlocks.
* **Resolution / Fix:**
  1. The multi-machine primitives are retained, but heartbeat/TTL parameters are calibrated to local Ollama inference latencies.
  2. Pre-flight health checks verify Hermes Gateway responsiveness before board instantiation.

---

### Issue 4: Maintenance Friction (8 Site-Packages Patches)
* **Assistant 3's Position:** Maintaining 8 local `site-packages` patches to bridge missing native hooks in the upstream Hermes framework creates high code fragility. Any `pip upgrade` silently wipes out patches and breaks production.
* **Architectural Rebuttal:** The 8 patches represent an accepted, one-time integration cost required to adapt generic agent frameworks to bounded daily workflows.
* **Resolution / Fix:**
  1. Move custom skill execution and role adapters into `./lib/hermes/` (e.g., `skills_provider.py`) to minimize touchpoints with upstream files.
  2. Pin upstream dependencies strictly in `pyproject.toml` to prevent silent breakage during updates.

---

### Issue 5: Structural Isolation & Fallback Policy
* **Assistant 3's Position:** When the Hermes Gateway crashes or times out, `manage.py` should silently fall forward into the batch pipeline (`llm_pipeline/`) to ensure report generation never fails.
* **Architectural Rebuttal:** Cross-pipeline fallbacks create tight coupling between `agentic/hermes/` and `llm_pipeline/`, masking genuine multi-agent defects and violating clean separation of concerns.
* **Resolution / Fix:**
  1. **Zero Import Inversion:** `agentic/hermes/` must interact **only** with adapters in `./lib/hermes/` and shared tools in `./lib/`. It has zero imports from `llm_pipeline/`.
  2. **Fail-Loud Policy:** If the Hermes Gateway or Kanban board fails, `manage.py go --fresh` raises an explicit `RuntimeError` and exits immediately with a non-zero exit code.

---

## 4. Current Compromise & Parity Gate

Per **ADR-002**, Track 3 remains active purely as a **bounded benchmark experiment** subject to hard exit criteria:

| Parity Gate Metric | Target Threshold | Validation Method |
| :--- | :--- | :--- |
| **Total Stories Processed** | $\ge 55$ stories | Telemetry evaluation (`t3_metrics.py`) |
| **Category Coverage** | $11 / 11$ categories represented | Diagnostic waterfall check |
| **Provenance Gap** | $\le 5\%$ gap vs batch baseline | Source URL verification against `llm_pipeline/` |
| **Gateway Isolation** | 0 imports from `llm_pipeline/` | Pre-flight runtime check & test suite |

If Track 3 meets parity using `qwen3.6:35b` and `./lib/hermes/` adapters, it remains an available multi-agent runtime. If context degradation or orchestration tax persists beyond the threshold, Track 3 will be formally archived per ADR-002.

