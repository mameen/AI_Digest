# Hermes + agentic config templates

Committed **examples only** — placeholders, no secrets. Copy to real locations locally.

| Template | Copy to | Purpose |
|---|---|---|
| [`hermes.env.example`](hermes.env.example) | `~/.hermes/.env` or `~/.hermes/profiles/<profile>/.env` | Slack tokens, allowlist (Hermes gateway) |
| [`hermes.config.example.yaml`](hermes.config.example.yaml) | merge into `~/.hermes/config.yaml` | Slack platform behaviour |
| [`digest.agentic.example.yaml`](digest.agentic.example.yaml) | merge into repo `config.yaml` | In-repo agentic model routing (future runner) |
| [`../../admin/config/templates/config.yaml`](../../admin/config/templates/config.yaml) | repo `config.yaml` restore via `nuke config` | LLM pipeline (Ollama) |

## Quick setup (Slack + Hermes)

```bash
# 1. Hermes secrets (never in repo)
mkdir -p ~/.hermes
cp agentic/hermes/config/hermes.env.example ~/.hermes/.env
chmod 600 ~/.hermes/.env
# edit ~/.hermes/.env — fill xoxb-, xapp-, U… IDs

# 2. Optional Slack tuning in Hermes config
# Append or merge hermes.config.example.yaml into ~/.hermes/config.yaml

# 3. Start gateway
python agentic/hermes/admin/manage.py hermes gateway start
```

While experimenting, scratch notes + pasted secrets: [`../slack_deleteme.md`](../slack_deleteme.md) (gitignored).

Proper steps: [`../slack.md`](../slack.md).

## Where secrets live

| Location | Committed? | Contents |
|---|---|---|
| `*.example` in this folder | Yes | Placeholders only |
| `~/.hermes/.env` | No | Real tokens |
| `slack_deleteme.md` | No (gitignored) | Temporary scratch |
| repo `.env` | No (gitignored) | Optional cloud LLM keys for pipeline |

See root [`.env.example`](../../.env.example) for pipeline-only env vars.
