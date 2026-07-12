# Day 3 Skills Review

> **Central Registry:** The complete skill inventory is maintained in [`/SKILL_store.md`](../../../SKILL_store.md) at the repo root. This file is the source of truth for all skills, their usage, examples, and status. Use SKILL_store.md as your first reference — this page documents the SKILL.md format specification.

## The SKILL.md Format (Official Spec)

Source: https://learn.microsoft.com/en-us/agent-framework/agents/skills

A Skill is a self-contained, portable unit of agent capability — a directory that bundles everything the agent needs on demand, without pre-loading it all into context.

### Structure

```
<skill-name>/
├── SKILL.md          # Required — frontmatter + natural-language instructions
├── scripts/          # Executable code the agent can invoke via run_skill_script
├── references/       # Reference docs loaded on demand via read_skill_resource
└── assets/           # Templates, examples, static resources
```

### SKILL.md Frontmatter Fields

```yaml
---
name: skill-name
description: What the skill does and when to use it. Max 1024 chars. Include task keywords.
license: Apache-2.0
compatibility: Requires python3
metadata:
  author: your-team
  version: "1.0"
allowed-tools: tool_one tool_two
---
```

| Field | Required | Rules |
|---|---|---|
| `name` | Yes | Max 64 chars. Lowercase, numbers, hyphens only. Must match parent directory name. |
| `description` | Yes | What it does and **when to use it** — this is shown at advertise stage (~100 tokens). Include trigger keywords. |
| `license` | No | License name or reference to bundled license file |
| `compatibility` | No | Max 500 chars. Environment requirements (OS, packages, network access) |
| `metadata` | No | Arbitrary key-value pairs (author, version, team) |
| `allowed-tools` | No | Space-delimited pre-approved tools the skill may call. Experimental. |

The markdown body after the frontmatter contains step-by-step instructions, examples, edge cases. Keep SKILL.md under 500 lines — move detailed reference material to `references/`.

### Progressive Disclosure — 4 Stages

This is the core mechanic. The agent loads only what it needs, when it needs it:

| Stage | Tokens | What happens |
|---|---|---|
| **Advertise** | ~100 per skill | Skill names + descriptions injected into system prompt at run start |
| **Load** | < 5000 recommended | Agent calls `load_skill` when a task matches — full SKILL.md body arrives |
| **Read resources** | as needed | Agent calls `read_skill_resource` to fetch from `references/` or `assets/` |
| **Run scripts** | as needed | Agent calls `run_skill_script` to execute from `scripts/` |

`load_skill` is always advertised. `read_skill_resource` only if the skill has resources. `run_skill_script` only if the skill has scripts.

### How to Write an Effective Skill

1. **Description is your only hook at advertise time** — write it as one clear action sentence with the trigger words a task would naturally contain.
2. **Instructions go in the body, not the frontmatter** — step-oriented, short, assume general context is already known.
3. **Move bulk content to `references/`** — policies, FAQs, schemas; the agent fetches them only when needed.
4. **Put runnable logic in `scripts/`** — the agent calls it as a tool rather than reasoning through it, which is more reliable.
5. **Put examples and templates in `assets/`** — for grounding, not in main instructions.
6. **Version explicitly** — `metadata.version` lets callers pin a version and detect staleness.
7. **Keep SKILL.md under 500 lines** — if it grows beyond that, refactor into references.

### Skills vs Workflows

| | Skills | Workflows |
|---|---|---|
| Who decides execution path | The AI | You (explicit steps) |
| Best for | Creative, adaptive, single-domain tasks | Deterministic, multi-step business processes |
| Failure recovery | Retry whole turn | Checkpoint and resume from last step |
| Side effects | Low-risk / idempotent | Structured — prevents double-execution |
| Rule of thumb | *If you want the AI to figure out how* | *If you need to guarantee what steps run and in what order* |

---

## Skill Kinds: By Delivery Mechanism (4 Official Types)

The spec defines four ways to *package and supply* a skill:

| Kind | How defined | Best for |
|---|---|---|
| **File-based** | `SKILL.md` directory on disk with optional `scripts/`, `references/`, `assets/` | Portable, version-controlled, human-editable. The canonical format. |
| **Code-defined (Inline)** | Built entirely in code as strings/delegates | Dynamic content generated at runtime (per-user, per-session, DB-driven) |
| **Class-based** | A typed class with annotated resource/script members | Packaged as a shared library; consumers add with one call |
| **MCP-based** | Discovered from an MCP server via `skill://index.json` (`skill-md` or `archive` sub-types) | Remote registries or team MCP servers. Archive scripts are **never executed** (security) |

---

## Skill Kinds: By Functional Purpose (11 Authoring Patterns)

These are the *what does it do* categories. A single SKILL.md can combine several.

| # | Type | What it does | Codelab example |
|---|---|---|---|
| 1 | **Instructional** | Step-by-step guidance, rules, output format, edge cases — the "classic" SKILL.md | `git-commit-formatter` (Level 1) |
| 2 | **Workflow / Procedural** | Defines a multi-step process the agent must follow in order | PR security review, expense approval |
| 3 | **Domain Expertise** | Packages specialized knowledge (finance rules, legal workflows, data pipelines) | Expense policy skill |
| 4 | **Task-Specific** | Narrow, trigger-matched skills that only activate for one task | Commit formatter, doc generator |
| 5 | **Tool-Usage** | Teaches the agent to invoke deterministic scripts rather than reason through the answer | `database-schema-validator` (Level 4) |
| 6 | **Reference / Context** | Provides supporting docs (FAQ, policy, schema) the agent loads on demand from `references/` | `license-header-adder` (Level 2) |
| 7 | **Few-Shot / Example-Driven** | Uses concrete input → output examples in `assets/` or `examples/` instead of verbose instructions | `json-to-pydantic` (Level 3) |
| 8 | **Decision-Framework** | Teaches the agent *how to think*: heuristics, prioritization, review methodology | Code review rubric skill |
| 9 | **Role-Definition** | Defines a persona the agent should adopt (architect, reviewer, security auditor) | Security STRIDE skill (Day 4) |
| 10 | **Template-Driven** | Provides scaffolds the agent fills in: component templates, test skeletons, report formats | License header template |
| 11 | **Composite / Multi-File** | Full capability package combining scripts, examples, references, and templates | `database-schema-validator` + `license-header-adder` combined |

### Codelab progression (Levels 1–4)

The Antigravity skills codelab structures authoring into escalating complexity:

| Level | Codelab skill | Pattern | What it demonstrates |
|---|---|---|---|
| 1 | `git-commit-formatter` | Instructions only | Pure instructional — no assets or scripts |
| 2 | `license-header-adder` | Instructions + `resources/` | Offload static text to a reference file |
| 3 | `json-to-pydantic` | Instructions + `examples/` | Few-shot pattern beats verbose instructions |
| 4 | `database-schema-validator` | Instructions + `scripts/` | Deterministic script beats LLM reasoning for binary checks |

### Key insight

Use a **script** (Level 4) whenever the answer is binary (pass/fail, valid/invalid) — LLMs are unreliable for rules that require exact matching. Use **examples** (Level 3) when the task involves many implicit style decisions that are hard to express in text.

---

## Skills Inventory

| # | Skill | What it does | Status | Implementation | Full SKILL.md structure |
|---|---|---|---|---|---|
| 1 | `source_discovery` | Find candidate items from RSS feeds, web pages, and video metadata using the config registry | ⚠️ Partial — registry done, real fetch not yet wired | `tools/news_sources.py` · `load_source_registry()` · `sources_by_kind()` | ❌ Not yet |
| 2 | `source_normalization` | Map heterogeneous source records (rss, web, youtube) into the unified `NewsItem` schema | ✅ Implemented | `tools/news_sources.py` · `normalize_source_records()` | ❌ Not yet |
| 3 | `dedupe_and_rank` | Collapse duplicate stories by title+host, score by relevance keywords, return top N | ✅ Implemented | `tools/selection.py` · `dedupe_items()` · `rank_items()` | ❌ Not yet |
| 4 | `brief_synthesis` | Assemble ranked items into a dated `DailyBrief` with `BriefCard` entries and a theme | ✅ Implemented | `workflow.py` · `run_daily_brief()` | ❌ Not yet |
| 5 | `artifact_validation` | Validate the brief dict against the `DailyBrief` Pydantic schema before publish | ✅ Basic | `validation/schemas.py` · `validate_brief()` | ❌ Not yet |
| 6 | `baseline_eval` | Load llm_pipeline baseline metrics from `app/index.json`, compute parity gap, pass/fail threshold | ✅ Implemented | `tools/baseline_eval.py` · `evaluate_brief_against_index()` | ❌ Not yet |

## Review Checklist

- [ ] Keep these six skill names as final labels
- [ ] Decide which two to harden into full SKILL.md structures first (recommendation: `source_discovery` and `dedupe_and_rank`)
- [ ] Create `skills/` directory alongside `src/` for the formal skill packages
