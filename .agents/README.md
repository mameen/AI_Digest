# AI Agent Configuration

> **Canonical narrative for the product story:** [`README.md`](../README.md) at the
> repo root. This directory is contributor onboarding; if anything here conflicts
> with README, **README wins**.

This directory is the **source of truth** for contributor onboarding on the AI Digest
project. It is committed to Git and read by both humans and automation. The
rulebook, editor rules, tool scaffolding, repo-level skills, and deeper
narrative all live here.

## Why this exists

The goal is to let *any* future LLM or new human contributor become productive
on this repo quickly, without having to reverse-engineer intent from the code.
The docs here capture the architecture, the run/debug workflow, the recurring
pitfalls, and the non-negotiable principles that make this a showcase project.

## Layout

```text
.agents/
|-- README.md                       # This file: the convention
|-- AGENTS.md                       # Day-to-day agent rulebook, source of truth
|-- SKILLS/                         # Repo-level agent skills, not runtime app skills
|   `-- i-have-adhd/
|-- .claude/                        # Claude local scaffold
|   |-- example.settings.local.json
|   `-- settings.local.json
|-- .cursor/rules/
|   `-- ai-digest-agent.mdc         # Cursor always-on rules, source of truth
|-- .opencode/                      # OpenCode local scaffold
|   |-- example.opencode.json
|   `-- opencode.json
`-- onboarding/
    |-- architecture.md             # Architecture and design summary
    |-- running-and-tooling.md      # How to run; what each tool/module is for
    |-- debugging-and-pitfalls.md   # Known failures, trace paths, fixes
    |-- principles-and-workflow.md  # Core principles and local change workflow
    `-- hermes-and-repo.md          # Hermes profiles: repo, env, PII, git boundaries
```

## Repo-Root Symlinks

Some tools only look at the repo root or their own config directory. Those paths
are **symlinks** into this directory. Edit the files under `.agents/`; root links
follow automatically.

| Link | Target |
|---|---|
| `AGENTS.md` | `.agents/AGENTS.md` |
| `SKILLS/` | `.agents/SKILLS/` |
| `.claude/` | `.agents/.claude/` |
| `.cursor/rules/ai-digest-agent.mdc` | `.agents/.cursor/rules/ai-digest-agent.mdc` |
| `.opencode/` | `.agents/.opencode/` |

There is no `AGENT.md` alias; use `AGENTS.md` or `.agents/AGENTS.md` only.

### Tool Scaffold Rules

- Treat `.agents/` as the editable home for all agent scaffolding.
- Treat repo-root `AGENTS.md`, `SKILLS/`, `.claude/`, `.cursor/rules/`, and
  `.opencode/` as compatibility entry points for tools that expect those paths.
- Keep example files safe to commit. Local settings may exist for tool behavior,
  but must not contain secrets, tokens, host credentials, or private API keys.
- Do not commit installed dependencies or generated caches from tool scaffolds.
  OpenCode keeps `node_modules`, package manifests, and lockfiles ignored unless
  the maintainer explicitly decides to vendor them.
- Repo-level skills in `.agents/SKILLS/` shape how contributors and coding
  agents work. They are different from product/runtime skills under `agentic/`.

## Relationship to `AGENTS.md`

`AGENTS.md` in this directory is the **single** agent rulebook. It carries the
principles index, an onboarding pointer table, and the day-to-day rules
(testing policy, leaderboard source kinds, versioning, commit/push). The
`onboarding/` docs hold the full narrative behind those rules. Keep them
consistent: a rule is stated once in `AGENTS.md` and expanded in onboarding.

## Reading Order

1. [`README.md`](../README.md): showcase story, ORIO roles, production GO.
2. `.agents/README.md`: this file, layout, symlinks, tool scaffolding.
3. `AGENTS.md`: day-to-day rules.
4. `onboarding/principles-and-workflow.md`: rules of engagement before coding.
5. `onboarding/architecture.md`: agentic GO and shared library stages.
6. `onboarding/running-and-tooling.md`: how to run and what each piece does.
7. `onboarding/debugging-and-pitfalls.md`: what to check when something breaks.

**Hermes profiles (`orio_*`):** read `onboarding/hermes-and-repo.md` for imports,
env, PII/commit policy, and git boundaries. That doc is referenced from each
profile SOUL.

## Maintenance

- These docs are **living**. When you change the pipeline, a parser, the widget,
  the schema, or a source, update the matching onboarding doc in the same change.
- Keep each file focused and short. Prefer editing an existing doc over adding a
  new one.
- No secrets, credentials, or personal access tokens ever live here.
- Edit agent files under `.agents/`; root symlinks follow automatically.
