# Hermes — agentic digest (`agentic/hermes/`)

> **Canonical narrative:** [`README.md`](../../README.md) at the repo root — four-role
> ORIO crew, default GO = kanban, `go --pipeline` = batch escape hatch only.
> **If anything here conflicts with README, README wins.**

This tree is the **product**: Concierge control plane, kanban workers, reports,
diagnostics, and publish path. Shared ingest lives in `lib/ingest/`; grounding,
validate, and render reuse `llm_pipeline/` as **libraries** (not orchestration).

## Quick start

```bash
python agentic/hermes/admin/manage.py bootstrap
python agentic/hermes/admin/manage.py go --start 2026-07-09 --history 10 --fresh
```

Batch debug only: `go --pipeline --start …`

## Docs (seven files — all extend root README)

| Doc | Question |
|---|---|
| [`../../README.md`](../../README.md) | **Showcase story, mascots, quick commands** |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How GO works + approved design |
| [`system_roles.md`](system_roles.md) | Who — four profiles, task graph |
| [`working_agreements.md`](working_agreements.md) | What — artifacts, tools, invariants |
| [`POC.md`](POC.md) | Bootstrap + E2E runbook |
| [`admin/README.md`](admin/README.md) | `manage.py` commands + digest-tools |
| [`slack.md`](slack.md) | Slack front desk + config templates |

## Layout

```
agentic/hermes/
├── admin/                 # manage.py, hermes_roles.yaml, souls/
├── plugins/digest-tools/  # worker + Concierge tools
├── tools/                 # orchestration, publish, topics, synthesize
├── reports/               # production HTML + JSON
├── diagnostics/           # per-run waterfall
└── docs/ARCHITECTURE.md
```
