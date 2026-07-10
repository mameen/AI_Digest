# Pipeline admin

Lifecycle for the **staged digest pipeline** only — venv, cache, config templates, runs.

```bash
python admin/manage.py bootstrap
python admin/manage.py bootstrap --recreate-venv
python admin/manage.py nuke ephemeral --yes
python admin/manage.py nuke config --yes
python admin/manage.py nuke run PREFIX --yes
python admin/manage.py doctor
python admin/manage.py status
```

Manifest + templates: [`config/`](config/).

## Agentic Hermes (separate)

Profiles, kanban, Ollama setup, dashboard passthrough:

```bash
python agentic/hermes/admin/manage.py bootstrap
python agentic/hermes/admin/manage.py setup
python agentic/hermes/admin/manage.py hermes dashboard
```

See [`../agentic/hermes/admin/README.md`](../agentic/hermes/admin/README.md) and
[`../agentic/hermes/POC.md`](../agentic/hermes/POC.md).

## Digest web UI

`feat/admin-local-server` branch: `python run.py --server` → `/admin/`.

## Testing

`tests/test_manage.py` — pipeline CLI. `tests/test_hermes_manage.py` — agentic admin.
