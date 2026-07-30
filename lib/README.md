### 1. Clear Library Structure & Boundary Rules

To prevent code duplication, "patch drift," and circular dependencies, the shared business logic is strictly decoupled into modular layers:

```
AI_Digest_2/
├── lib/                     # 🟢 Shared Core Utilities (Domain Agnostic & Clean)
│   ├── agent_tools.py        # Generic tool execution helpers
│   ├── bundle.py             # Feed bundle processing & ingestion logic
│   ├── report_source.py      # Source mapping and URL extraction
│   └── hermes/               # 🟡 Hermes Adapters & Extensions
│       └── admin/
│           └── skills_provider.py # Progressive disclosure skill provider
│
├── llm_pipeline/            # 🔵 Deterministic Pipeline Tail (Grounding, Validate, Render)
│   ├── grounding.py          # Grounding, reflection, & URL verification
│   ├── validate.py           # Report schema verification & contract enforcement
│   └── render.py             # Output report generation (Markdown/JSON)
│
└── agentic/hermes/          # 🟣 Track 3 Runtime (Hermes Agentic Experiment)
    ├── admin/                # Management CLI & Pre-flight checks
    └── docs/                 # Documentation & Architecture Decision Records (ADRs)

```

---

### 2. Captured Reusability & Dependency Rules

In **`ADR-001-extract-shared-pipeline.md` (ADR-002)** and **Issue #0001**, we codified four strict software engineering rules:

1. **Zero Import Inversion:**
* `agentic/hermes/` is **never allowed** to import from `llm_pipeline/`.
* Both runtimes import shared logic from `./lib/` and the deterministic tail directly.


2. **Shared Business Logic via `./lib`:**
* Source parsing, URL extraction, and feed bundling are centralized in `./lib/` so both batch (`llm_pipeline/`) and agentic (`agentic/hermes/`) pipelines use identical, tested code paths.


3. **Adapter Isolation in `./lib/hermes/`:**
* Instead of hacking upstream framework code, custom skill loading and framework adapters live in `./lib/hermes/admin/skills_provider.py`.
* This limits maintenance friction and ensures upstream dependencies stay cleanly pinned in `pyproject.toml`.


4. **Deterministic Tail Reuse:**
* Both pipelines re-use the exact same deterministic tail (`grounding.py` → `validate.py` → `render.py`). Agents handle intelligence and discovery; python scripts handle strict schema validation and file rendering.



---

### Summary Table: Where Each Contract Lives

| Contract / Structural Element | Location in Docs / Code | Reusability Impact |
| --- | --- | --- |
| **Shared Library Utilities** | `./lib/` | Centralized I/O, feed discovery, and source parsing used by all tracks. |
| **Skill Loading Standard** | `./lib/hermes/admin/skills_provider.py` | Implements progressive disclosure based on `agentskills.io` standard. |
| **Pipeline Boundary Rule** | `ADR-001-extract-shared-pipeline.md` | Enforces zero cross-pipeline imports between `agentic/hermes/` and `llm_pipeline/`. |
| **Output Contract Enforcement** | `track_3_issue_0001.md` (Section 3) | Formally defines JSON/Markdown card formats passed between agent roles. |