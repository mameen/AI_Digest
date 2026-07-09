# ADR-002: Repo layout — pipeline vs agentic/hermes

**Status:** Accepted (planning — phased execution)  
**Date:** 2026-07-05  
**Scope:** Repository layout, deprecation path, admin ownership  

**Related:** [001](001-local-ollama-with-per-role-model-routing.md), [../ARCHITECTURE.md](../ARCHITECTURE.md)

---

## Context

We are running **two tracks**:

1. **Staged LLM pipeline** (`llm_pipeline`, `run.py`) — showcase digest, under
   evaluation; may be deprecated if agentic Hermes wins A/B.
2. **Agentic Hermes** (`agentic/hermes/`) — parallel roles, Concierge, kanban,
   Slack; experimental.

Goals:

- **Clear separation:** everything agentic lives under `agentic/hermes/` so we
  can delete or archive the pipeline later without archaeology.
- **Pipeline admin** (browser dashboard, `run.py --server`) stays with the
  pipeline track — still under evaluation on `feat/admin-local-server`, not
  mixed into Hermes.
- **Cherry-pick hygiene:** small commits (e.g. uv bootstrap) can land on `main`
  without dragging agentic scaffold.

Current friction on `feat/agentic-hermes-architecture` (resolved):

- ~~`admin/manage.py` served both pipeline and Hermes~~ — split complete.
- `llm_pipeline/` + `pipeline/` shims already split code from imports, but
  `run.py`, `config.yaml`, `reports/` still live at repo root (pipeline-shaped).

---

## Decision

### 1. Keep `main` layout stable for now

**Do not** introduce a top-level `pipeline/` umbrella directory or move `run.py`
yet. Reasons:

- `main` is protected and shippable; large moves churn tests, docs, and GitHub
  Pages paths.
- Agentic POC is not proven; restructuring twice (llm_pipeline move + pipeline/
  folder) adds cost without validation benefit.
- The existing **`llm_pipeline/` + `pipeline/` shim** on the agentic branch is
  enough separation for code until deprecation.

Revisit a physical `pipeline/` tree **after** A/B or explicit deprecate decision.

### 2. Target mental model (document now, migrate later)

```
Repo root (pipeline era — eventually shrink or delete)
├── run.py, run_tests.py, config.yaml
├── llm_pipeline/          # implementation
├── pipeline/              # import shims → llm_pipeline
├── reports/, diagnostics/, vendor/
├── admin/                 # pipeline-only: web dashboard + digest lifecycle
└── …

agentic/hermes/            # self-contained agentic product (survives deprecation)
├── admin/                 # manage.py, config/hermes_roles.yaml, .runtime nuke
├── config/                # hermes.env.example, agentic models snippet
├── tools/baseline.py      # read-only adapters into llm_pipeline
├── .runtime/              # gitignored agent state
├── docs/, POC.md, slack.md, system_roles.md, …
└── run_hermes.py          # future entry (Phase 4)
```

**Rule:** New agentic code **only** under `agentic/hermes/`. New pipeline code
stays in `llm_pipeline/` (or `main`’s `pipeline/` until merge).

### 3. Admin ownership split

| Concern | Location | Branch |
|---|---|---|
| Digest web admin (`run.py --server`, `/admin/`) | `admin/index.html`, `admin-app.js`, `llm_pipeline/admin_*` | `feat/admin-local-server` |
| Pipeline bootstrap / nuke cache / digest templates | `admin/manage.py`, `admin/config/` | `main` or admin branch — **pipeline** |
| Hermes bootstrap, `.runtime` nuke, `hermes` CLI passthrough | **`agentic/hermes/admin/manage.py`** | `feat/agentic-hermes-architecture` |
| Hermes dashboard / Slack / kanban | Upstream Hermes — not rebuilt here | — |

**Near-term task:** done — pipeline `admin/manage.py`; agentic `agentic/hermes/admin/manage.py`.

### 4. Deprecation path (when agentic wins)

1. Stop running `run.py` for production digests; Hermes becomes primary.
2. Keep `agentic/hermes/tools/baseline.py` temporarily for ingest parsers /
   grounding / render reuse.
3. Archive or delete: `llm_pipeline/`, shims, `run.py`, pipeline `admin/`,
   `config.yaml` enrich passes — **not** `agentic/hermes/`.
4. Optional final rename: collapse surviving shared libs into
   `agentic/hermes/tools/legacy/` then delete.

If pipeline wins: delete `agentic/hermes/.runtime` and experimental runner;
keep docs as research archive.

### 5. Optional future: top-level `pipeline/` directory

If we want a **physical** bundle before deletion (not needed now):

```
pipeline/
├── llm/                   # today’s llm_pipeline/
├── shims/                 # today’s pipeline/ re-exports
├── admin/                 # digest web + manage.py
├── run.py                 # or symlink at root
└── README.md
```

**Defer** until maintainer approves deprecation or monorepo-style clarity is
worth the move cost.

---

## Consequences

### Positive

- Clear “what survives” boundary: `agentic/hermes/` is the long-lived tree.
- `main` stays calm; agentic branch carries experiments.
- Admin confusion reduced: Hermes admin lives under `agentic/hermes/admin/`.

### Negative / work queued

- [x] Move Hermes CLI from `admin/manage.py` → `agentic/hermes/admin/manage.py`
- [x] Update POC.md / README paths
- [ ] Keep pipeline `admin/` only on admin branch until merged

---

## Alternatives considered

| Option | Why not now |
|---|---|
| Big-bang `pipeline/` folder on agentic branch | High churn, two refactors back-to-back |
| Everything in repo root forever | Agentic/pipeline keep mixing (admin, docs) |
| Monorepo with separate git repos | Overkill for portfolio project |
| Delete `llm_pipeline` rename, only `pipeline/` | Already shipped shims; rename again adds noise |

---

## Where this plan lives

| Doc | Role |
|---|---|
| **This ADR** | Layout + deprecation — source of truth |
| [`../../README.md`](../../README.md) | Index + status |
| [`../ARCHITECTURE.md`](../ARCHITECTURE.md) | Technical agentic design |
| `.agents/onboarding/architecture.md` | Update when pipeline deprecated on `main` |

---

## Recommendation summary

**Simpler for now:** keep `main` as-is; on the agentic branch keep
`llm_pipeline/` + shims; **move agentic ops into `agentic/hermes/`**; leave
pipeline web admin on `feat/admin-local-server`. Revisit top-level `pipeline/`
folder only when deprecating the staged pipeline.
