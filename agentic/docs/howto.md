# Hermes quick commands

```cmd
.\.venv\Scripts\activate
python agentic\hermes\admin\manage.py hermes profile use default
python agentic\hermes\admin\manage.py hermes profile use orio_concierge
python agentic\hermes\admin\manage.py hermes profile use orio_researcher
python agentic\hermes\admin\manage.py hermes profile use orio_librarian
python agentic\hermes\admin\manage.py hermes profile use orio_synthesizer
```

## What this does

- activates the repo Python environment
- switches each profile on
- keeps all five profiles ready to run

## Note

- `default` is the root profile
- the `orio_*` profiles are the Orio crew
