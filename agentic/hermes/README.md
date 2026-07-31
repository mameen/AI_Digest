# Hermes Multi-Agent POC

This POC explores AI Digest as a four-role Hermes kanban crew:

| Role | Responsibility |
|---|---|
| Concierge | Starts a run, creates the board, tracks status |
| Researcher | Fetches and grounds topic-specific notes |
| Librarian | Deduplicates, groups, and prepares the synthesis skeleton |
| Synthesizer | Produces digest-ready structured content |

The deterministic Python tail still validates, grounds, and renders the final
report. The approved published outputs live in [`../../app/`](../../app/).

## Why Keep This POC

Hermes is useful as a reference implementation because it makes role boundaries,
handoffs, diagnostics, and orchestration cost visible. It is not the leanest
runtime for this bounded daily digest workload, but it is strong portfolio
evidence for multi-agent system design and evaluation.

## Run

```powershell
python agentic/hermes/admin/manage.py bootstrap
python agentic/hermes/admin/manage.py go --start 2026-07-09 --history 10 --fresh
```

Requires a working Hermes gateway and local Ollama-compatible model setup.

## Outputs

| Output | Path |
|---|---|
| Hermes reports | [`reports/`](reports/) |
| Hermes diagnostics | [`diagnostics/`](diagnostics/) |
| Approved website copies | [`../../app/reports/`](../../app/reports/) and [`../../app/diagnostics/`](../../app/diagnostics/) |

When deciding what was approved for publication, prefer `../../app/`.

## Useful Docs

| Topic | Doc |
|---|---|
| Runbook | [`POC.md`](POC.md) |
| Architecture | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Role contracts | [`working_agreements.md`](working_agreements.md) |
| Role definitions | [`system_roles.md`](system_roles.md) |
| Admin commands | [`admin/README.md`](admin/README.md) |
