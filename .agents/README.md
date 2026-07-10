# AI Agent Configuration

> **Canonical narrative for the product story:** [`README.md`](../README.md) at the
> repo root. This directory is contributor onboarding; if anything here conflicts
> with README, **README wins**.

This directory is the **source of truth** for contributor onboarding on the AI Digest
project. It is committed to Git and read by both humans and automation. The
rulebook, editor rules, and deeper narrative all live here.

## Why this exists

The goal is to let *any* future LLM (or new human contributor) become productive
on this repo quickly, without having to reverse-engineer intent from the code.
The docs here capture the architecture, the run/debug workflow, the recurring
pitfalls, and the non-negotiable principles that make this a showcase project.

## Layout

```
.agents/
├── README.md                       # This file — the convention
├── AGENTS.md                       # Day-to-day agent rulebook (source of truth)
├── .cursor/rules/
│   └── ai-digest-agent.mdc         # Cursor always-on rules (source of truth)
└── onboarding/
    ├── architecture.md             # Architecture & design summary
    ├── running-and-tooling.md      # How to run; what each tool/module is for
    ├── debugging-and-pitfalls.md   # What went wrong, how to debug/trace, fixes
    └── principles-and-workflow.md  # Core principles + the local change workflow
```

## Repo-root symlinks (for tool compatibility)

Some tools only look at the repo root or `.cursor/rules/`. Those paths are
**symlinks** into this directory — edit the files here, not the links:

| Link | Target |
|---|---|
| `AGENTS.md` | `.agents/AGENTS.md` |
| `.cursor/rules/ai-digest-agent.mdc` | `.agents/.cursor/rules/ai-digest-agent.mdc` |

There is no `AGENT.md` alias; use `AGENTS.md` (or `.agents/AGENTS.md`) only.

## Relationship to `AGENTS.md`

`AGENTS.md` in this directory is the **single** agent rulebook. It carries the
principles index, an onboarding pointer table, and the day-to-day rules
(testing policy, leaderboard source kinds, versioning, commit/push). The
`onboarding/` docs hold the full narrative behind those rules. Keep them
consistent: a rule is stated once in `AGENTS.md` and expanded here.

## Reading order for a new agent

1. [`README.md`](../README.md) — showcase story, ORIO roles, production GO (canonical).
2. `.agents/README.md` — this file (layout and symlinks).
3. `AGENTS.md` — day-to-day rules.
4. `onboarding/principles-and-workflow.md` — rules of engagement (read before coding).
5. `onboarding/architecture.md` — agentic GO + shared library stages.
6. `onboarding/running-and-tooling.md` — how to run and what each piece does.
7. `onboarding/debugging-and-pitfalls.md` — when (not if) something breaks.

## Maintenance

- These docs are **living**. When you change the pipeline, a parser, the widget,
  the schema, or a source, update the matching onboarding doc in the same change.
- Keep each file focused and short. Prefer editing an existing doc over adding a
  new one.
- No secrets, credentials, or personal access tokens ever live here.
- Edit agent files under `.agents/`; root symlinks follow automatically.
