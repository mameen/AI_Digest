## 📣 Announcement (Discord / LinkedIn)

Hi all,

I'd love your feedback on my capstone: **AI Digest — a single-agent AI/ML news
aggregator** built on Google's Agent Development Kit (ADK 2.0). It turns the daily
arXiv firehose into a ranked, 10-story brief with a one-line "why it matters" per
story.

Under the hood it's a real ADK agent, not a hard-coded pipeline:
🔹 a **`google.adk` Agent + Runner + InMemorySessionService** runtime
🔹 a model-chosen **`FunctionTool`** that pulls live arXiv `cs.AI` / `cs.LG` feeds
🔹 **Gemini** (`gemini-flash-latest`) via the `google.genai` SDK for ranking + explanations
🔹 a **self-critique loop** — a curator drafts the brief, a critic reviews it for
duplicates / vague reasoning / poor ordering, and the curator revises until approved
🔹 a deterministic keyword fallback + schema validation, so it always emits a valid
10-card brief even with no API key or network

Two shifts stuck with me building this:

**1. From multi-agent graphs → a single agent with progressive context.** My
instinct (and my current production pipeline) was a graph: concierge → researchers
→ librarian → synthesizer. It works, but every hand-off re-reads overlapping
context, and you end up with summaries of summaries — context rot. The course
reframed it: one agent that decides what it reads on demand (advertise → load →
read → run), so context stays fresh. Simpler, and honestly more maintainable.

**2. From code assistance → a factory model with intent-driven development.** The
real unlock isn't autocomplete. It's expressing intent — "discover, dedupe, rank,
validate, brief" — and letting deterministic steps (a validation script beats LLM
guessing for any pass/fail check) do the exact work. You stop writing steps and
start governing outcomes.

📓 Kaggle notebook 👉 https://www.kaggle.com/code/ameenmohameddemiry/ai-digest-single-agent-news-aggregator

---

# Self-Evaluation: `kaggle_submission.ipynb` vs. Competing Submissions

_Critical review conducted 2026-07-13. Scope: all notebooks in this folder._

## TL;DR

The submission is honest but hollow. It ranks **middle of the pack**: better than
five thin/stub notebooks on completeness, but decisively behind the three strongest
entries on genuine agent knowledge and clear use of Google ADK.

## What `kaggle_submission.ipynb` actually is (73 cells)

A deterministic, keyword-scoring pipeline wearing an agent costume. The notebook
itself admits this:

> This notebook uses a custom `ADKAgent` class (ADK-style orchestration).
> It does **not** register an agent with official `google.adk` runtime APIs.

### Concrete problems

1. **No real agent behavior.** `ADKAgent.forward()` is a hardcoded
   `discover -> rank -> validate` sequence. No LLM-driven reasoning, no
   model-initiated tool calls, no planning, no memory/session, no loop.
   `tool_discover()` is literally `return items` (a passthrough).
2. **No genuine ADK.** All 4 occurrences of `google.adk` are *disclaimers* saying
   ADK is not used. No `from google.adk import Agent`, no `Runner`, no
   `SessionService`, no `FunctionTool`.
3. **The one "AI" path is effectively dead code.** It imports the deprecated
   `google.generativeai` SDK and calls `genai.GenerativeModel('gemini-pro')` — a
   retired model on a legacy SDK. Without a key (the Kaggle default) it immediately
   falls back to keyword scoring. So "3 backends" really means one keyword sorter
   that runs, plus two paths that almost never execute.
4. **The "ranking" is a keyword tally.** `+3` model/llm/agent, `+3` benchmark,
   `+2` ai/ml. On the fallback data every item scores identically, so results are
   essentially alphabetical.
5. **Massive duplication.** The `ADKAgent` class is redefined ~5 times (Part A,
   Part B, Part C.3, Part C Demo 2). The Demo 2 version doesn't even rank — it calls
   `create_stub_brief()`.
6. **Cosmetic strengths only.** Pydantic models with constraints, stdlib RSS
   parsing, HTTPS validation, JSON export. Real but table-stakes plumbing, not agent
   work.

## Competitive field

| Notebook | Cells | Real ADK? | Real LLM? | Verdict |
|---|---|---|---|---|
| **careercraft** | 38 | Yes — `google-adk` + `google.genai`, Runner, SessionService, `google_search` | Yes | Far ahead. 6 specialized agents, SKILL.md progressive disclosure, HITL checkpoints, self-critique loop, trajectory/token logging, PDF export, mock mode |
| **pak-banking** | 3 | Yes — `from google.adk import Agent` + BigQuery `FunctionTool` on Vertex AI | Yes | Short but authentic single-agent-with-tool on real SBP data |
| **medminder** | 80 | Partial — writes an ADK agent *package* to disk (scaffolding, not live run) | Partial | Large, polished, but ADK is generated as files rather than imported/run |
| **financial-audit** | 28 | No | No (sklearn) | No LLM, but genuinely engineered: IsolationForest + TF-IDF anomaly detection, simulated MCP server, guardrails, orchestration router, strong visuals |
| **this submission** | 73 | No (disclaimed) | Dead path | Keyword pipeline; verbose; honest but hollow |
| career-guidance | 3 | No | No | Thin/incomplete |
| examease | 5 | No | No | Thin |
| revenue-recovery | 5 | No | No | Thin |
| rolemorph | 1 code | No | No | Mostly markdown |
| laiba-haroon | 1 | No | No | Stub |

## Verdict

Beats the five thin/stub notebooks on completeness and polish. Loses decisively to:

- **CareerCraft** — the only submission that fully wires real ADK to course
  concepts (skills, sessions, HITL, observability, self-reflection). The reference
  for "clear use of Google ADK."
- **pak-banking** — tiny but real: an ADK `Agent` with a working `FunctionTool`
  against live data.
- **financial-audit** — no ADK, but more actual agent *engineering* (real ML, MCP
  simulation, guardrails) than this submission.

Relative to the top three, the submission is "fake": it shows no agent knowledge and
explicitly no ADK, and its 73-cell length works against it by repeating a thin idea.

## What would close the gap

The notebook's volume is a liability, not an asset.

1. **Use real ADK.** Replace `ADKAgent` with `from google.adk import Agent` +
   `Runner` + `InMemorySessionService`. Register `discover`, `rank`, `validate` as
   real `FunctionTool`s the model chooses to call. pak-banking (3 cells) is a minimal
   template.
2. **Make the LLM path primary and current.** Drop `google.generativeai`/`gemini-pro`;
   use `from google import genai` with a current Gemini model; keyword scoring as
   fallback only.
3. **Cut ~60% of the notebook.** Delete Part A and Part C demo duplicates; keep one
   clean end-to-end build. One real agent beats three fake ones.
4. **Add one genuinely agentic behavior** — e.g., a self-critique/re-rank loop or the
   model deciding whether to re-fetch — so there is actual reasoning, not a fixed
   pipeline.
