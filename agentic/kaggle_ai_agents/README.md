# Kaggle AI Agents

Standalone capstone sandbox for the Kaggle AI Agents course.

This POC is intentionally self-contained: course notes, day-by-day planning,
skills, tests, examples, and submission materials all stay inside this folder.

## Read First

| Topic | Doc |
|---|---|
| Task overview and setup | [`HOWTO.md`](HOWTO.md) |
| Architecture notes | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Backend options | [`docs/PLUGGABLE_BACKENDS.md`](docs/PLUGGABLE_BACKENDS.md) |
| Evaluation guide | [`docs/EVALUATION_GUIDE.md`](docs/EVALUATION_GUIDE.md) |
| Skill contracts | [`skills/`](skills/) |
| Submission notes | [`submission/README.md`](submission/README.md) |

## What It Proves

1. A single-agent, skills-driven workflow can replace a heavier multi-agent
   graph for this class of capstone project.
2. Tool contracts, evaluation, and security gates can be documented and tested
   in one small repo.
3. The project can be run and reviewed without needing the broader AI Digest
   runtime.

## Suggested Entry Points

```bash
PYTHONPATH=src pytest agentic/kaggle_ai_agents/tests -q
PYTHONPATH=src python -c "from kaggle_ai_agents.workflow import run_daily_brief_with_backend; print(run_daily_brief_with_backend('direct_script', use_real_sources=False))"
```

## Archive Rule

Keep this folder focused on the capstone POC. Move new shared or repo-wide
rules to the root docs or `SKILLS/` instead of duplicating them here.
