# agentic/

Agentic proof-of-concept work for AI Digest.

The archive-facing story lives in the root [`README.md`](../README.md). This
directory contains three of the four POCs:

| POC | Directory | Role |
|---|---|---|
| Hermes Multi-Agent | [`hermes/`](hermes/) | Four-role kanban reference implementation |
| Kaggle AI Agents | [`kaggle_ai_agents/`](kaggle_ai_agents/) | Standalone course/capstone sandbox |
| Single Agent + Skills | [`single_hermes_agent/`](single_hermes_agent/) | Target design direction and skill-loading notes |

## Boundaries

1. Keep product/runtime skills under `agentic/`.
2. Keep repo-assistant skills under [`../SKILLS/`](../SKILLS/).
3. Keep generated website artifacts under [`../app/`](../app/) as the approved
   published output.
4. Do not introduce new cross-runtime coupling without documenting the reason in
   the affected POC README.

## POC Status

| Directory | Status |
|---|---|
| [`hermes/`](hermes/) | Reference implementation; useful for architecture comparison and diagnostics |
| [`kaggle_ai_agents/`](kaggle_ai_agents/) | Standalone training/capstone material |
| [`single_hermes_agent/`](single_hermes_agent/) | Design stub for the future single-agent-with-skills shape |

For repo-wide coding and verification rules, read [`../AGENTS.md`](../AGENTS.md).
