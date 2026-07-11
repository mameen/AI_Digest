# ORIO Skills-First Ideation: Transitioning to Agent Skills

This document outlines the ideation and architectural design for transitioning **ORIO** from a complex, multi-agent Hermes kanban crew into a modular, lightweight **Single-Agent-with-Skills** setup (the "Agent Skills" approach).

---

## 1. The Core Shift: Why Refactor?

The current Hermes multi-agent configuration split the digest creation across 4 separate profiles (Concierge, Researcher, Librarian, Synthesizer) communicating via a kanban board. While conceptually elegant, this multi-agent model introduces significant friction:
* **Orchestration Tax**: Complex handoffs, prompt chain synchronization, and multiple points of failure.
* **Context Rot**: The Librarian fan-in step floods the context window with raw text, triggering the "lost in the middle" effect.
* **Testing Hardness**: High complexity in isolating errors or running regressions.

Following the principles in the **Agent Skills** (Day 3) course, we are refactoring ORIO to use a **single runtime agent** that dynamically loads specialized **Skills** on demand.

---

## 2. Proposed Skills Library (`agentic/agent_skills/skills/`)

Instead of maintaining separate agent runtimes, we will package ORIO's capabilities into modular directories adhering to the `SKILL.md` progressive disclosure standard:

```
agentic/agent_skills/skills/
├── feed_ingestion/          # Skill: Fetch and parse curated RSS, YouTube, and leaderboard endpoints
├── story_curation/          # Skill: Classify, deduplicate, and score daily stories
└── digest_synthesis/        # Skill: Generate structured prose summaries and JSON schema output
```

### Skill 1: Feed Ingestion (`feed_ingestion`)
* **What it does**: Fetches raw feeds, parses YouTube transcripts/chapters, crawls leaderboard tables via Crawl4AI, and retrieves structured JSON API leaderboards (SWE-bench, EvalPlus).
* **Deterministic boundary**: Offloads crawling and API fetching to background python scripts, returning structured markdown tables and JSON stubs to the agent.

### Skill 2: Story Curation (`story_curation`)
* **What it does**: Groups incoming stories, identifies duplicate reports, and assigns them to the core category checklist (e.g., `llm`, `robotics`, `rag`, `design-ai`).
* **Progressive Disclosure**: Only loaded during the cataloging phase, avoiding prompt bloat during writing.

### Skill 3: Digest Synthesis (`digest_synthesis`)
* **What it does**: Takes the curated story mapping and generates the daily summary takeaway, category-level overview narratives, and final formatted story card details.
* **State Decoupling**: Outputs directly to the target `digest.json` schema without maintaining the conversation history.

---

## 3. Retaining ORIO's Strengths

1. **Deterministic Grounding Guard**: The grounding validation tail (verifying link truth with python code, demoting ungrounded URLs to `source_pending`) will remain as a core software invariant.
2. **Decoupled State**: State will continue to route via file systems (`.preflight/`, `reports/index.json`) acting as our decoupled file message bus, preventing context window bloat.
3. **Mascots and UI**: The user-facing dashboard, diagnostics waterfalls, and cute role mascots will be maintained in the UI.

---

## 4. Next Steps
1. Create the `agentic/agent_skills/skills/` directory structure.
2. Draft the `SKILL.md` schemas and YAML frontmatter for each of the core skills.
3. Scaffold the runner script to load and execute these skills sequentially inside a single agent runtime.
