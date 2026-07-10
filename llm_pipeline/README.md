# llm_pipeline — shared digest libraries (+ batch escape hatch)

> **Canonical narrative:** [`README.md`](../README.md) at the repo root. **Production GO**
> is the four-role ORIO kanban crew under `agentic/hermes/` — not this package's
> batch orchestration.

This package holds **shared** ingest/enrich/validate/render code: a local-first,
deterministic four-stage flow (`ingest → enrich → validate → render`) that uses
a local LLM (Ollama + Instructor) to score, summarize, and gap-fill stories,
with a grounding guard and auditable provenance.

**Orchestration:** deprecated batch CLI (`run.py`) and `manage.py go --pipeline`
call into here. Agentic GO reuses grounding, validate, and render from this tree.

## Relationship to `pipeline/`

`pipeline/` at the repo root is a **compatibility shim** that re-exports this
package. Existing entry points (`run.py`, tests, admin ops) import `pipeline.*`
unchanged. New code — especially under `agentic/hermes/` — should import
`llm_pipeline` directly.

## What this is (and is not)

| This package | Not this |
|---|---|
| Staged batch pipeline with structured LLM calls | Agentic fan-out / fan-in orchestration |
| Deterministic grounding guard | LLM-as-judge for link truth |
| Fixed enrich passes (skeleton → gap → carry) | Dynamic task boards driven by chat |
| One report per scheduled run | Per-target parallel workers + synthesizer |

The agentic **product** lives in [`../agentic/hermes/`](../agentic/hermes/).

## Entry points

```bash
python run.py                    # batch escape hatch (deprecated orchestration)
python run.py --skeleton-only    # skip LLM enrich
python run_tests.py              # unit tests (import pipeline shims)
```

## Modules (high level)

- **Ingest:** `fetch.py`, `leaderboards.py`, `structured_sources.py`
- **Enrich:** `enrich.py`, `editorial.py`, `llm_client.py`, `tools.py`
- **Validate:** `validate.py`, `grounding.py`
- **Render:** `render.py`, `diagnostics.py`, frame/nav/footer helpers
- **Ops:** `admin_ops.py`, `local_server.py`, `doctor.py`

Full architecture: [`.agents/onboarding/architecture.md`](../.agents/onboarding/architecture.md).
