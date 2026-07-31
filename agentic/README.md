# Agentic

Agentic proof-of-concept work for AI Digest lives here.

## POCs

| POC | Folder | Purpose |
|---|---|---|
| Hermes Multi-Agent | [`hermes/`](hermes/) | Four-role kanban reference implementation |
| Kaggle AI Agents | [`kaggle_ai_agents/`](kaggle_ai_agents/) | Standalone course/capstone sandbox |
| Single Agent + Skills | [`single_hermes_agent/`](single_hermes_agent/) | Future direction for a smaller runtime with skills |

## Read First

| Topic | Doc |
|---|---|
| Agentic governance | [`AGENTS.md`](AGENTS.md) |
| Hermes overview | [`hermes/README.md`](hermes/README.md) |
| Kaggle overview | [`kaggle_ai_agents/README.md`](kaggle_ai_agents/README.md) |
| Single-agent ideation | [`single_hermes_agent/docs/ideation.md`](single_hermes_agent/docs/ideation.md) |

## Rules

1. Keep runtime-specific skills under `agentic/`.
2. Keep repo-assistant skills under [`../SKILLS/`](../SKILLS/).
3. Keep published website artifacts under [`../app/`](../app/) as the canonical public output.
