# lib/ — Shared Library Ownership & Structure

## Ownership

| Track / Agent | Owns | Scope |
|---|---|---|
| **Agent 2 (T2)** | `lib/*.py` | Generic shared utilities extracted from `llm_pipeline/` — domain-agnostic code reused by all tracks |
| **Agent 3 (T3)** | `lib/hermes/` | Hermes-specific adapters, wrappers, integrators, artifact gates, and runtime store — only T3 touches these files |

**Rule:** Agent 2 extracts generic libs to `lib/*.py`. T3 creates, manages, and updates `lib/hermes/` with Hermes-specific code. No cross-over — T3 never edits `lib/*.py` (non-hermes), Agent 2 never edits `lib/hermes/`.

## Structure

```
AI_Digest_2/
├── lib/                     # 🟢 Shared Core Utilities (T2 owns *.py)
│   ├── agent_tools.py        # Generic tool execution helpers
│   ├── bundle.py             # Feed bundle processing & ingestion logic
│   ├── report_source.py      # Source mapping and URL extraction
│   ├── hermes/               # 🟡 Hermes-specific (T3 owns this directory)
│   │   ├── __init__.py       # Package init
│   │   ├── skills_provider.py  # Progressive disclosure skill provider (T3-B)
│   │   ├── artifacts.py        # Artifact validation gates (T3-D)
│   │   └── runtime_store.py    # Runtime artifact cache (T3-D)
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

## Dependency Rules

1. **Zero Import Inversion (Goal):** `agentic/hermes/` should eventually be **never allowed** to import from `llm_pipeline/`. Currently, `manage.py` imports from `llm_pipeline.diagnostics`, `llm_pipeline.environment`, and `llm_pipeline.validate` — known violations being tracked in the placeholder map.

2. **Shared Business Logic via `./lib`:** Source parsing, URL extraction, and feed bundling are centralized in `./lib/` so both batch (`llm_pipeline/`) and agentic (`agentic/hermes/`) pipelines use identical, tested code paths.

3. **Adapter Isolation in `./lib/hermes/` (T3-D complete):** T3 owns `lib/hermes/`. Custom skill loading, artifact validation, and runtime persistence live here. This limits maintenance friction and ensures upstream dependencies stay cleanly pinned in `pyproject.toml`.

4. **Deterministic Tail Reuse:** Both pipelines re-use the exact same deterministic tail (`grounding.py` → `validate.py` → `render.py`). Agents handle intelligence and discovery; Python scripts handle strict schema validation and file rendering.

## T2 Placeholder Map

32 imports across 12 files in `agentic/hermes/` still reference `llm_pipeline/` directly. These will be wired to `lib/` once Agent 2 completes extraction:

| llm_pipeline Module | Target lib/ Module | Imports in agentic/hermes/ | Files Affected |
|---|---|---|---|
| `llm_pipeline.editorial` | `lib/editorial.py` | 6 | 5 files |
| `llm_pipeline.validate` | `lib/validate.py` | 3 | 3 files |
| `llm_pipeline.enrich` | `lib/enrich.py` | 2 | 2 files |
| `llm_pipeline.grounding` | `lib/grounding.py` | 2 | 2 files |
| `llm_pipeline.history` | `lib/history.py` | 2 | 2 files |
| `llm_pipeline.diagnostics` | `lib/diagnostics.py` | 5 | 3 files |
| `llm_pipeline.llm_client` | `lib/llm_client.py` | 2 | 2 files |
| `llm_pipeline.environment` | `lib/environment.py` | 1 | 1 file |
| `llm_pipeline.render` | `lib/render.py` | 1 | 1 file |
| `llm_pipeline.diagnostics_frame` | `lib/diagnostics_frame.py` | 1 | 1 file |

Full details: [`agentic/hermes/docs/track_2_3_todo_placeholders.md`](../agentic/hermes/docs/track_2_3_todo_placeholders.md)

## Summary: Where Each Contract Lives

| Contract / Structural Element | Location | Owner | Reusability Impact |
|---|---|---|---|
| **Shared Library Utilities** | `./lib/*.py` | Agent 2 (T2) | Centralized I/O, feed discovery, source parsing used by all tracks |
| **Hermes Adapters & Extensions** | `./lib/hermes/` | Agent 3 (T3) | Hermes-specific validation, persistence, skill loading |
| **Pipeline Boundary Rule** | `ADR-001-extract-shared-pipeline.md` | — | Goal: zero cross-pipeline imports between `agentic/hermes/` and `llm_pipeline/`. Currently violated in `manage.py`. |
| **Output Contract Enforcement** | `track_3_issue_0001.md` (Section 3) | T3 | Defines JSON/Markdown card formats passed between agent roles |
