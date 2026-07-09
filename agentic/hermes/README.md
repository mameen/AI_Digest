# Hermes — agentic digest architecture (experimental)

Parallel, role-based agents that fan out research work, fan in through a
synthesizer, and deliver a finished report — inspired by the
[Hermes parallel-agents walkthrough](docs/202607_research/hermes-parallel-agents-walkthrough.md).

This tree is **experimental**. It does not replace `llm_pipeline` or `run.py`.
The staged pipeline keeps shipping while Hermes is developed and A/B-tested
against it.

**Layout & deprecation plan:** [docs/adr/002-repo-layout-and-pipeline-deprecation.md](docs/adr/002-repo-layout-and-pipeline-deprecation.md) — agentic stays in this folder; pipeline admin stays on `feat/admin-local-server`; no big-bang `pipeline/` move on `main` yet.

## Design principles (from research)

1. **Agent = role, not subject.** One researcher profile handles N targets; do
   not clone an agent per company/category.
2. **Fan-out / fan-in.** Parallel workers post artifacts; a synthesizer waits on
   parent tasks before composing the final digest.
3. **Goal prompts, not step prompts.** Tell agents *what* to produce and *how it
   should look*; let them figure out tooling/setup.
4. **Separate list updates from execution.** “Add Linear” updates memory; “GO”
   builds the board — two distinct intents.
5. **Scheduled jobs ping; chat replies act.** Cron cannot block on user input.

## Layout

```
agentic/hermes/
├── README.md
├── MANUAL_BOOTSTRAP.md
├── admin/                    # manage.py, config/hermes_roles.yaml
├── config/                   # *.example templates (no secrets)
├── system_roles.md
├── working_agreements.md
├── slack.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── adr/
│   └── 202607_research/
├── tools/
│   └── baseline.py
└── .runtime/                 # gitignored agent state
```

## Documentation index

| Doc | Primary question | Contents |
|---|---|---|
| [`system_roles.md`](system_roles.md) | **Who?** | Roles, tiers, orchestration, task graph, Concierge intents |
| [`working_agreements.md`](working_agreements.md) | **What & how?** | Schemas, tools, invariants, per-role do/don't, handoffs |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Component diagram, A/B baseline, open decisions |
| [`docs/202607_research/…`](docs/202607_research/hermes-parallel-agents-walkthrough.md) | Hermes video/Notion research capture |
| [`docs/adr/…`](docs/adr/002-repo-layout-and-pipeline-deprecation.md) | **Layout plan** — pipeline vs agentic/hermes, what moves when |
| [`docs/adr/…`](docs/adr/001-local-ollama-with-per-role-model-routing.md) | ADRs — local Ollama default, per-role models, CLI config |
| [`MANUAL_BOOTSTRAP.md`](MANUAL_BOOTSTRAP.md) | **Learn Hermes** — hand-run bootstrap before `setup` |
| [`admin/README.md`](admin/README.md) | Agentic admin — `manage.py`, role profiles |
| [`POC.md`](POC.md) | **Start here** — proof Hermes chat/kanban/Slack before integration |
| [`slack.md`](slack.md) | Slack + Hermes setup steps |
| [`config/…`](config/README.md) | Env/config **templates** (placeholders — safe to commit) |

## Using llm_pipeline as baseline

Hermes tools can call into the existing pipeline for ingestion parsers,
grounding rules, render helpers, and fixtures — without importing the full
staged runner:

```python
from agentic.hermes.tools.baseline import ingest_preflight, render_from_json
```

See `tools/baseline.py` and `docs/ARCHITECTURE.md` for the adapter surface.

## Status

| Component | Status |
|---|---|
| **POC guide (test before integrate)** | Done — [`POC.md`](POC.md) |
| Research capture | Done — `docs/202607_research/` |
| Architecture sketch | Done — `docs/ARCHITECTURE.md` |
| System roles | Done — `system_roles.md` |
| Working agreements | Done — `working_agreements.md` |
| Kanban / task orchestration | Done — `go` / `generate-report` |
| Agent profiles + artifact validators | Done — worker dispatch path |
| Telegram / cron automation | Not started |
| A/B harness vs `llm_pipeline` | Stub in `tools/baseline.py` |
| Production editorial quality | Use `run.py` (agentic uses baseline carry-forward) |

## Branch

Development happens on `feat/agentic-hermes-architecture` (or topic branches
cut from it). Do not merge to `main` until Hermes can produce a comparable
digest with traceable provenance.
