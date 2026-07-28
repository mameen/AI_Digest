# Agent Skills Specification (agentskills.io)

> **Aligned with:** [agentskills.io specification](https://agentskills.io/specification)  
> **Reference:** [Microsoft Learn — Agent Skills](https://learn.microsoft.com/en-us/agent-framework/agents/skills?pivots=programming-language-csharp)

---

## What is a Skill?

A skill is a self-contained, portable unit of agent capability — a directory that bundles everything the agent needs on demand, without pre-loading it all into context.

---

## Skill Structure

```
<skill-name>/
├── SKILL.md          # Required — frontmatter + natural-language instructions
├── scripts/          # Executable code the agent can invoke via run_skill_script
├── references/       # Reference docs loaded on demand via read_skill_resource
└── assets/           # Templates, examples, static resources
```

---

## SKILL.md Frontmatter Fields

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
| `name` | Yes | Max 64 chars. Lowercase, numbers, and hyphens only. Must match parent directory name. |
| `description` | Yes | What it does and **when to use it** — shown at advertise stage (~100 tokens). Include trigger keywords. |
| `license` | No | License name or reference to bundled license file. |
| `compatibility` | No | Max 500 chars. Environment requirements (OS, packages, network access). |
| `metadata.author` | No | Team or author attribution. |
| `metadata.version` | No | Explicit version for pinning and staleness detection. |
| `allowed-tools` | No | Space-delimited pre-approved tools the skill may call. Experimental. |

The markdown body after frontmatter contains step-by-step instructions, examples, edge cases. Keep SKILL.md under 500 lines — move detailed reference material to `references/`.

---

## Progressive Disclosure — 4 Stages

This is the core mechanic. The agent loads only what it needs, when it needs it:

| Stage | Tokens | What happens |
|---|---|---|
| **Advertise** | ~100 per skill | Skill names + descriptions injected into system prompt at run start |
| **Load** | < 5000 recommended | Agent calls `load_skill` when a task matches — full SKILL.md body arrives |
| **Read resources** | as needed | Agent calls `read_skill_resource` to fetch from `references/` or `assets/` |
| **Run scripts** | as needed | Agent calls `run_skill_script` to execute from `scripts/` |

`load_skill` is always advertised. `read_skill_resource` only advertised when at least one skill has resources. `run_skill_script` only advertised when at least one skill has scripts.

---

## Skill Kinds: By Delivery Mechanism (4 Official Types)

| Kind | How defined | Best for |
|---|---|---|
| **File-based** | `SKILL.md` directory on disk with optional subdirs | Portable, version-controlled, human-editable. The canonical format. |
| **Code-defined (Inline)** | Built entirely in code as strings/delegates | Dynamic content generated at runtime (per-user, per-session, DB-driven). |
| **Class-based** | A typed class with annotated resource/script members | Packaged as a shared library; consumers add with one call. |
| **MCP-based** | Discovered from an MCP server via `skill://index.json` | Remote registries or team MCP servers. Archive scripts are **never executed** (security). |

---

## Skill Kinds: By Functional Purpose (11 Authoring Patterns)

| # | Type | What it does |
|---|---|---|
| 1 | **Instructional** | Step-by-step guidance, rules, output format, edge cases. |
| 2 | **Workflow / Procedural** | Defines a multi-step process the agent must follow in order. |
| 3 | **Domain Expertise** | Packages specialized knowledge (finance rules, legal workflows). |
| 4 | **Task-Specific** | Narrow, trigger-matched skills for one task only. |
| 5 | **Tool-Usage** | Teaches the agent to invoke deterministic scripts rather than reason. |
| 6 | **Reference / Context** | Supporting docs loaded on demand from `references/`. |
| 7 | **Few-Shot / Example-Driven** | Concrete input → output examples instead of verbose instructions. |
| 8 | **Decision-Framework** | Teaches the agent *how to think*: heuristics, prioritization. |
| 9 | **Role-Definition** | Defines a persona the agent should adopt. |
| 10 | **Template-Driven** | Provides scaffolds the agent fills in. |
| 11 | **Composite / Multi-File** | Full capability combining scripts, examples, references, templates. |

### Codelab progression (Levels 1–4)

| Level | Pattern | What it demonstrates |
|---|---|---|
| 1 | Instructions only | Pure instructional — no assets or scripts. |
| 2 | Instructions + `references/` | Offload static text to a reference file. |
| 3 | Instructions + `examples/` | Few-shot pattern beats verbose instructions. |
| 4 | Instructions + `scripts/` | Deterministic script beats LLM reasoning for binary checks. |

**Key insight:** Use a **script** (Level 4) whenever the answer is binary — LLMs are unreliable for rules that require exact matching. Use **examples** (Level 3) when the task involves many implicit style decisions.

---

## Skills vs Workflows

| | Skills | Workflows |
|---|---|---|
| Who decides execution path | The AI | You (explicit steps) |
| Best for | Creative, adaptive, single-domain tasks | Deterministic, multi-step business processes |
| Failure recovery | Retry whole turn | Checkpoint and resume from last step |
| Side effects | Low-risk / idempotent | Structured — prevents double-execution |
| Rule of thumb | *If you want the AI to figure out how* | *If you need to guarantee what steps run and in what order* |
