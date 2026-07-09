# Agentic Hermes admin

Lifecycle for **upstream Hermes** integration — role profiles, Ollama routing,
kanban toolset, `.runtime/` state. Pipeline bootstrap stays in [`../../../admin/`](../../../admin/).

```bash
python agentic/hermes/admin/manage.py bootstrap       # .runtime + setup
python agentic/hermes/admin/manage.py bootstrap --skip-setup
python agentic/hermes/admin/manage.py setup [--dry-run]
python agentic/hermes/admin/manage.py demo-board [--dry-run]  # Phase 2 POC graph
python agentic/hermes/admin/manage.py go [--fresh]          # workers: research → librarian → synthesizer → render
python agentic/hermes/admin/manage.py verify-handover       # smoke test (no HTML)
python agentic/hermes/admin/manage.py nuke --yes        # clear .runtime only
python agentic/hermes/admin/manage.py status
python agentic/hermes/admin/manage.py hermes dashboard
python agentic/hermes/admin/manage.py hermes profile list
```

Role definitions: [`config/hermes_roles.yaml`](config/hermes_roles.yaml).
SOUL templates: [`config/souls/`](config/souls/) (deployed to `~/.hermes/profiles/<role>/SOUL.md` by `setup`).

Architecture diagrams: [`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).
E2E runbook: [`../HANDOFF.md`](../HANDOFF.md).

**`setup` also configures:** `web.backend ddgs`, `tools post-setup ddgs`, researcher
`digest` toolset. One-time plugin symlink:
[`../plugins/digest-tools/README.md`](../plugins/digest-tools/README.md).

**Learn by hand first:** [`../MANUAL_BOOTSTRAP.md`](../MANUAL_BOOTSTRAP.md).

Env/config templates (no secrets): [`../config/`](../config/) (`hermes.env.example`, etc.).
