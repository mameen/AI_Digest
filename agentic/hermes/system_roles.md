# Hermes system roles (ORIO crew)

> **Canonical narrative:** [`README.md`](../../README.md) at the repo root. **If this
> doc conflicts with README, README wins.**

Canonical role model for the agentic digest pipeline. Each row is **one profile**
(reusable across many tasks). An agent is a **role**, not a subject — never fork
a profile per category, company, or feed.

**Board topics on GO:** By default, Concierge assembles one research task per
non-empty category from the **best known-good report** (highest story count that
passes validation). Override by pinning `demo_topics` in `hermes_roles.yaml`.

**Production GO** (`manage.py go` / Concierge `digest_go`) runs this graph.
Batch `run.py` parity is `go --pipeline` only (deprecated batch orchestration).

**ORIO** — *Open Research Intelligence Observatory* — is the internal codename for
AI Digest. Hermes profile names use the `orio_*` prefix; human-facing labels stay
**Concierge**, **Researcher**, **Librarian**, **Synthesizer**.

**Pipeline order:**

```
Concierge → Researcher × N (parallel) → Librarian → Synthesizer → grounding / validate / render
```

See also: [`working_agreements.md`](working_agreements.md) (artifact contracts,
tools vs pipeline invariants),
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## How this doc relates to `working_agreements.md`

The design is split on purpose — some topics touch both:

| Question | Read here (`system_roles.md`) | Read there (`working_agreements.md`) |
|---|---|---|
| **Who** runs in the pipeline? | Role definitions, tier, wait conditions | — |
| **Who** do I ask to add a topic? | Concierge | — |
| **What** may each role do / not do? | Responsibility tables per role | Do / do-not tables with contract detail |
| **What** shape does each role output? | One-line output summary | Full schemas (`researcher_artifact/v1`, etc.) |
| **What** tools can researchers call? | — | Tool list, `verify_url`, thresholds |
| **What** is *not* a role? | Pipeline invariants (one paragraph) | Grounding, validation, provenance taxonomy |
| **How** do handoffs connect? | Task graph | End-to-end data-flow diagram |

**Rule:** roles and orchestration live here; schemas, tools, and invariants live
in `working_agreements.md`. Cross-links under each role point to the matching
agreement section.

---

## Roles at a glance

| Role | Profile name | Display name | Model tier | Waits on | Delivers to |
|---|---|---|---|---|---|
| [Concierge](#concierge) | `orio_concierge` | Concierge | Smart | User / cron ping | Task board |
| [Researcher](#researcher) | `orio_researcher` | Researcher | Fast | Concierge arms task | Librarian |
| [Librarian](#librarian) | `orio_librarian` | Librarian | Smart | All researcher tasks | Synthesizer |
| [Synthesizer](#synthesizer) | `orio_synthesizer` | Synthesizer | Smart | Librarian task | Report output |

**Not an agent role:** grounding guard, validation gates, and provenance stamping
run deterministically in `llm_pipeline` after synthesis — auditable, not
LLM-judged. See [`working_agreements.md`](working_agreements.md) for how these
differ from tools, skills, and MCPs.

---

## Role definitions

### Concierge

**Also called:** front desk (UX metaphor). **Do not call:** supervisor — that
implies quality policing by LLM, which conflicts with the deterministic guard.

→ Working agreement: [`working_agreements.md` § Topics guideline](working_agreements.md#concierge-topics-guideline)

| | |
|---|---|
| **Purpose** | Single point of contact **and ORIO control plane**: standing topic list, schedule, intent routing, task-graph assembly, run lifecycle (kick/abort/status), report paths, assess/deploy/publish after maintainer approval. |
| **You ask them to…** | Add/remove a standing topic, change schedule, say `GO`, abort/reset the board, check status, open report paths, assess a run, deploy, commit/push (after you approve). |
| **Model tier** | Smart — must parse intent and never confuse “update list” with “run now”. |
| **Inputs** | Chat/admin messages, cron trigger, memory (topic list, builder prompt, schedule). |
| **Outputs** | Kanban tasks; confirmation counts (“N research + 1 librarian + 1 synthesizer”); assess JSON with absolute report paths; deploy/publish receipts. |
| **Does not** | Fetch sources, classify stories, write the digest, bypass config or grounding, push without explicit user approval. |

**Control plane tools (`digest_admin` + `kanban`):** `digest_go`, `digest_board_status`,
`digest_setup_board`, `digest_assess_run`, `digest_deploy_app`, `digest_publish`.
Assess returns `paths.report_html` (absolute) and `preview.report_local` (`file://`).
Publish commits staged `app/` + hermes artifacts; **`confirm_push: true`** only after
you explicitly approve push.

**Intent taxonomy (planned):**

| Intent | Action | Runs pipeline? |
|---|---|---|
| `ADD_TOPIC` | Append to standing memory / propose config diff | No |
| `REMOVE_TOPIC` | Drop from standing memory | No |
| `GO` | Fan out researchers + librarian + synthesizer | Yes |
| `EDIT_BUILDER` | Update synthesizer prompt in memory | No |
| `STATUS` | Report board state and last run | No |

**Schedule pattern:** cron **pings** (“today’s topics — edit or GO”); user **replies**
in normal chat. Scheduled jobs cannot block waiting for an answer.

---

### Researcher

→ Working agreement: [`working_agreements.md` § Researcher](working_agreements.md#researcher-working-agreement)

| | |
|---|---|
| **Purpose** | Parallel fetch-and-summarize worker pointed at one target (category, feed cluster, or source bundle). |
| **You ask them to…** | Nothing directly — Concierge creates and assigns tasks. |
| **Model tier** | Fast / cheap — read pages, extract facts, post structured summaries. |
| **Inputs** | Task description (target + window), ingestion context from `llm_pipeline` fetch/parsers. |
| **Outputs** | Task artifact: raw story stubs, summaries, links, source notes — see `researcher_artifact/v1` in [`working_agreements.md`](working_agreements.md). |
| **Does not** | Dedupe across topics, remap to standing topic list, merge categories, render the digest. |

**Reflect and ground (researcher's job):** before `kanban_complete`, each researcher
self-checks coverage and gaps, calls `verify_url` on every cited link, and ships an
honest `output.md` for **this target only**. That artifact is the researcher's
grounded view of its task.

**Trust boundary:** Librarian **assumes you did your job** for this target.
Synthesizer reads **`librarian.md` only** — neither re-fetches nor re-verifies your
links. Overlap across researchers is resolved by Librarian, not by you.

Publish-time grounding · validate · render runs **after Synthesizer** in deterministic
code — separate from your task-level diligence.

One profile handles every research task; only the **task body** changes per target.

---

### Librarian

→ Working agreement: [`working_agreements.md` § Librarian](working_agreements.md#librarian-working-agreement)

| | |
|---|---|
| **Purpose** | **Curatorial middle layer** between parallel research and final synthesis: sort, classify, regroup, dedupe, and map findings onto the standing **topics list** as a knowledge graph. |
| **You ask them to…** | Nothing directly — Concierge creates one librarian task per run; it wakes when all researchers finish. |
| **Model tier** | Smart — needs cross-document reasoning, taxonomy alignment, and merge decisions; cheaper than full report design. |
| **Inputs** | All researcher artifacts; standing topics list from Concierge memory / `config.yaml`; optional prior-run graph for continuity. |
| **Outputs** | **Curated digest skeleton** — see `librarian_artifact/v1` in [`working_agreements.md`](working_agreements.md): topic-aligned categories, deduped stories, knowledge graph, discovered topics with appendix hints. |
| **Does not** | Fetch new URLs, re-verify researcher links, change the standing topic list, apply publish-time grounding (downstream), or produce final HTML/PDF. |

**Trust boundary:** treat each researcher artifact as **already reflected and grounded**
for its target. Your job is curatorial merge — **resolve overlap**, map every article
and data point to the standing topic list, dedupe, regroup — so the Synthesizer
never has to redo classification or merge work.

**Why between researchers and synthesizer**

Researchers optimize for **coverage and speed** per target. The Synthesizer should
**not** inherit overlap disputes, category drift, or orphan data points. The
Librarian is the **single fan-in** that finishes all curatorial work before synthesis:

1. **Sort** — order by significance, recency, novelty within each topic.
2. **Classify** — assign each story to canonical topic IDs from the standing list.
3. **Regroup** — merge split coverage (same announcement from two feeds), split
   overloaded buckets, flag “misc” only when no topic fits.
4. **Knowledge graph mapping** — emit edges between stories/topics (`related_to`,
   `supersedes`, `same_event_as`, `feeds_topic`) so the Synthesizer can write
   executive narrative and charts with context, not a flat dump.

**Knowledge graph (librarian output shape, sketch):**

```yaml
topics: [aisearch, robotics, llm, ...]          # from Concierge standing list
nodes:
  - id: story:<hash>
    topic: robotics
    title: "..."
    significance: 4
edges:
  - from: story:a
    to: story:b
    rel: same_event_as
  - from: story:a
    to: topic:agentic-ai
    rel: feeds_topic
gaps:
  - topic: rag
    note: "No primary sources this window; carry-forward candidate"
overflow:
  - story: story:x
    note: "Below significance threshold; available if Synthesizer needs filler"
```

The Synthesizer reads this graph plus regrouped categories — **not** raw researcher
comments. Overlap and topic placement are **settled here**; Synthesizer writes.

---

### Synthesizer

→ Working agreement: [`working_agreements.md` § Author](working_agreements.md#author-synthesizer-working-agreement)

| | |
|---|---|
| **Purpose** | Compose the **finished digest** from the Librarian skeleton: executive takeaway, daily summary, category narratives, and schema-valid **`digest.json`**. |
| **You ask them to…** | Nothing directly — Concierge seeds the builder prompt in memory; one synthesizer task per run. |
| **Model tier** | Smart — positioning, prose, layout, chart design. |
| **Inputs** | Librarian curated skeleton + knowledge graph (overlap and topic mapping **already done**); builder prompt from memory; brand/style guide. |
| **Outputs** | Digest JSON via `synthesize_digest`; compatible with `llm_pipeline` render path. |
| **Does not** | Re-fetch sources, resolve overlap, reclassify or remap topics (Librarian's job), read raw researcher artifacts, hand-author full JSON, or skip downstream grounding/validation. |

**Focus:** format, data shape, and writing — turn `librarian.md` into publishable
`digest.json`. Do **not** redo curatorial merge, dedupe, or topic assignment.

Prompt style: **goal and output**, not install steps — hand a style guide and
section list; let the agent solve rendering setup.

---

## Task graph (per `GO`)

```mermaid
flowchart TB
    C[Concierge]
    R1[Researcher → topic A]
    R2[Researcher → topic B]
    Rn[Researcher → topic N]
    L[Librarian]
    S[Synthesizer]
    G[grounding + validate + render]

    C --> R1 & R2 & Rn
    R1 & R2 & Rn --> L
    L --> S
    S --> G
```

```yaml
# Example board after GO (4 standing topics)
tasks:
  - id: research-aisearch
    assignee: researcher
    parents: []
  - id: research-robotics
    assignee: researcher
    parents: []
  - id: research-llm
    assignee: researcher
    parents: []
  - id: research-design-ai
    assignee: researcher
    parents: []
  - id: librarian
    assignee: librarian
    parents: [research-aisearch, research-robotics, research-llm, research-design-ai]
  - id: synthesizer
    assignee: synthesizer
    parents: [librarian]
```

Concierge confirms: **“4 research + 1 librarian + 1 synthesizer.”**

---

## Comparison to deprecated batch path (`run.py` / `--pipeline`)

Historical mapping only — **production uses the agentic roles below**, not
sequential `enrich_digest` passes.

| Agentic role | Rough batch-path equivalent |
|---|---|
| Concierge | Human ops + trigger (now: control plane tools) |
| Researcher | Per-category enrich / preflight passes (parallelized) |
| Librarian | *Explicit* — curation, dedupe, cross-category merge, topic graph |
| Synthesizer | Daily summary + narrative compose + render input |
| Grounding guard | `grounding.py` + `validate.py` (unchanged, post-agent) |

The Librarian replaces implicit sorting that today happens inside sequential
enrich passes and gap-fill — but makes it **explicit, inspectable, and graph-shaped**
before the expensive final compose step.

---

## Model tier summary

| Tier | Roles | Rationale |
|---|---|---|
| Fast | Researcher | Fetch + summarize; many parallel calls |
| Smart | Concierge, Librarian, Synthesizer | Intent parsing, taxonomy/graph reasoning, editorial compose |

Local Ollama can host all roles initially; tier split matters when mixing cloud
models (e.g. flash researchers, pro synthesizer).

---

## Rules of engagement

1. **One profile per role** — scale by adding tasks, not cloning agents.
2. **Concierge owns the standing topic list** — board tasks derive from it (default: best report); Librarian maps *into* it, does not mutate it.
3. **Librarian is the only fan-in before synthesis** — Synthesizer never reads raw researcher output directly.
4. **Provenance is stamped by the pipeline**, not authored by any role.
5. **Grounding runs after Synthesizer** — deterministic demotion of bad links.
6. **List updates ≠ runs** — adding a topic never implies `GO`.

---

## Open questions

| Topic | Notes |
|---|---|
| Graph persistence | Store librarian graph per run prefix for diagnostics and trend charts? |
| Carry-forward | Librarian proposes carry candidates; Concierge/policy approves? |
| Topic list source of truth | Memory for speed, `config.yaml` for permanence — promotion flow TBD |
| Significance floor | Librarian filters vs Synthesizer uses overflow bucket |

Record decisions in this file as the design firms up.
