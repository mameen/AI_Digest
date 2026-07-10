# Agentic Hermes admin

> **Canonical narrative:** [`README.md`](../../../README.md) at the repo root. **If this
> doc conflicts with README, README wins.**

Lifecycle for **upstream Hermes** integration — role profiles, Ollama routing,
kanban toolset, `.runtime/` state.

```bash
python agentic/hermes/admin/manage.py bootstrap       # .runtime + setup
python agentic/hermes/admin/manage.py bootstrap --skip-setup
python agentic/hermes/admin/manage.py setup [--dry-run]
python agentic/hermes/admin/manage.py go --start YYYY-MM-DD --fresh   # production kanban (default)
python agentic/hermes/admin/manage.py go --pipeline --start YYYY-MM-DD   # batch run.py escape hatch
python agentic/hermes/admin/manage.py go --prefix P --pipeline --skip-ingest  # re-enrich from cache
python agentic/hermes/admin/manage.py demo-board [--dry-run]
python agentic/hermes/admin/manage.py verify-handover       # kanban smoke test (no HTML)
python agentic/hermes/admin/manage.py nuke --yes        # clear .runtime only
python agentic/hermes/admin/manage.py status
python agentic/hermes/admin/manage.py hermes dashboard
python agentic/hermes/admin/manage.py hermes profile list
```

## GO modes

| Command | What runs |
|---------|-----------|
| `go` (default) | Concierge → research × N → librarian → synthesizer → render |
| `go --pipeline` | Batch `enrich_digest` (same as `run.py`) — debug/A/B only |

Role definitions: [`config/hermes_roles.yaml`](config/hermes_roles.yaml).
SOUL templates: [`config/souls/`](config/souls/) (deployed to `~/.hermes/profiles/<role>/SOUL.md` by `setup`).

Architecture: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
Runbook: [`../POC.md`](../POC.md).

Env/config templates (no secrets): [`../config/`](../config/) (`hermes.env.example`, etc.).

## digest-tools plugin

`setup` symlinks [`../plugins/digest-tools/`](../plugins/digest-tools/) into
`~/.hermes/plugins/digest-tools` and configures `web.backend ddgs`.

| Toolset | Profiles | Purpose |
|---|---|---|
| **`digest`** | `orio_researcher`, `orio_librarian`, `orio_synthesizer` | Lazy ingest + synthesis |
| **`digest_admin`** | `orio_concierge` | GO, board, assess, open report, deploy, publish |

**Worker tools (`digest`):** `verify_url`, `fetch_rss`, `read_preflight_category`,
`read_crawl_markdown`, `read_structured_json`, `read_topic_config`, `synthesize_digest`

**Concierge tools (`digest_admin`):** `digest_go`, `digest_board_status`,
`digest_setup_board`, `digest_assess_run`, `digest_open_report`, `digest_deploy_app`,
`digest_publish` (push only with `confirm_push: true`)

Search uses Hermes **`web_search`** via `web.backend ddgs`.

## Hermes redeploy (after SOUL / tool / patch changes)

Re-run when you change SOUL templates, `hermes_roles.yaml`, digest-tools, kanban
patches, or orchestration code loaded by the plugin:

```bash
python agentic/hermes/admin/manage.py setup
hermes gateway restart
python agentic/hermes/admin/manage.py hermes dashboard   # reopen if tab was open
```

**First-time / cold start** (no gateway yet):

```bash
python agentic/hermes/admin/manage.py bootstrap
hermes gateway start
python agentic/hermes/admin/manage.py hermes dashboard
```

Verify: `python agentic/hermes/admin/manage.py hermes doctor` and
`hermes profile list`. Dry-run deploy: `setup --dry-run`.
