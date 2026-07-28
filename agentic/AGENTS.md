# agentic/ — Agent Layer Governance

**Status:** Active  
**Date:** 2026-07-27

---

## Purpose

This directory houses the agentic layer for AI Digest. It is organized into four tracks per [ADR-002](hermes/docs/ADR-001-extract-shared-pipeline.md):

| Track | Directory | Status |
|---|---|---|
| **Track 1** | — | `llm_pipeline/` (root) — immutable parity benchmark |
| **Track 2** | — | Extract shared libs → `lib/` (root) |
| **Track 3** | `hermes/` | Multi-agent kanban crew — stabilize as bounded experiment, never default |
| **Track 4** | `single_hermes_agent/` | Single-agent-with-skills — production default target |

---

## Track 2: Shared Lib Extraction (In Progress)

We are currently extracting deterministic, reusable utilities from `llm_pipeline/` into the root-level `lib/` package. This eliminates `sys.path.insert` hacks and enables clean imports for both the batch pipeline and the future single-agent runtime.

**See:** [`llm_pipeline/AGENTS.md`](../llm_pipeline/AGENTS.md) for the full extraction plan, scope, and workflow.

### What Happens Next

Once the shared lib extraction is complete:

1. **Wire extracted modules to skills** — The single-agent runtime will import from `lib/` as skill implementations (feed_ingestion, story_curation, digest_synthesis).
2. **Skills load metadata only** (~100 tokens), full `SKILL.md` activates on trigger.
3. **State routes via filesystem** (`preflight/`, `.cache/`), not conversation history.

**Timeline:** Skill wiring begins after Track 2 extraction is complete and parity is proven. No shortcuts.

---

## Track 3: Hermes (Multi-Agent Kanban)

- **Status:** Bounded experiment — never set as default
- **Pin upstream version**, log orchestration telemetry, enforce strict exit criteria
- Archive if metrics degrade beyond threshold
- **Reference docs:** [`hermes/docs/`](hermes/docs/)

---

## Track 4: Single-Agent-with-Skills

- **Status:** In progress — production default target
- Progressive skill discovery, file-based state routing
- Deterministic tail calls to `llm_pipeline.validate_and_render()`
- Hierarchical routing prevents selection degradation as scope grows

---

## Rules

1. **Never remove from `llm_pipeline/` before parity.** See [`llm_pipeline/AGENTS.md`](../llm_pipeline/AGENTS.md).
2. **Test the real thing.** No mocks — use real fixtures (see `.agents/AGENTS.md` testing policy).
3. **Branch → test → PR.** Never push without explicit permission; `main` is protected.
4. **No agent co-author trailers.** Commits are maintainer-only.

---

## References

- [ADR-002](hermes/docs/ADR-001-extract-shared-pipeline.md) — Four-track pivot strategy
- [Track 1 TODO #001](hermes/docs/track_1_todo_001.md) — Coverage baseline & action items
- [`llm_pipeline/AGENTS.md`](../llm_pipeline/AGENTS.md) — Extraction plan & coverage snapshots
- [.agents/AGENTS.md](../../.agents/AGENTS.md) — Repo-wide agent rules
