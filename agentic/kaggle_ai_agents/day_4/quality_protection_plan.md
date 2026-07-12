# Quality Protection Plan

Three threats to guard against in any LLM agent workflow:

1. **Hallucination** — the agent fabricates facts, links, or scores
2. **Context rot (dilution)** — context degrades over long tool-calling loops; later steps see summaries of summaries
3. **Drift** — output quality shifts away from the baseline over time without being noticed

---

## The Harness and the Loop

From the Agent Framework docs:

> A harness drives the agent: it runs the loop that calls the model and executes the tools the model asks for, manages conversation history and context so the model stays within its limits, applies approval and safety policies before actions are taken, and keeps the agent progressing toward task completion.

The **harness** is not optional scaffolding — it is the engine. Key capabilities relevant to our three threats:

| Harness capability | Threat it addresses |
|---|---|
| **Tool-calling loop** with iteration limit | Hallucination — agent uses deterministic tools rather than reasoning through facts |
| **Compaction** (token-budget-aware) | Context rot — prevents long loops from overflowing and degrading context |
| **Per-call history persistence** | Drift — crash recovery + inspection mid-run; every state is auditable |
| **Todo list provider** | Context rot — agent tracks progress explicitly; doesn't re-read history to know where it is |
| **Looping evaluators** | Hallucination/Drift — re-invokes until a quality condition is met |
| **OpenTelemetry** | Drift — observable trace per run for comparison and anomaly detection |
| **Agent mode (Plan/Execute)** | Context rot — planning is interactive, execution is autonomous; clear phase separation |

Skills also reflect on their own work — a skill can include a `scripts/` validator that the agent calls after producing output. The loop re-runs if the script returns a non-zero exit code.

---

## Protection by Threat

### 1. Hallucination

Root cause: LLM reasoning over facts it does not know.

Controls in this project:

| Control | Where |
|---|---|
| Source grounding — every card links to a real URL | `models.py` — `HttpUrl` field, Pydantic rejects non-URLs |
| Script-backed validation for binary checks | `validation/schemas.py`, Day 4 STRIDE gate |
| `baseline_eval` compares story count and significance against known-good baseline | `tools/baseline_eval.py` |
| Provenance field preserved through normalization | `normalize_source_records()` in `news_sources.py` |
| Never cite a URL without verifying it | tool contract in `source_contracts.md` |

### 2. Context Rot / Dilution

Root cause: too much accumulated context; agent attention degrades on what matters.

Controls in this project:

| Control | Where |
|---|---|
| Progressive skill loading — only the active skill's context is in the window | `skills/` directory (planned); Day 3 architecture |
| `RunState` phase tracking — agent does not re-read history to find its place | `state.py` |
| Artifact-first boundaries — each phase produces a structured artifact, not prose | `artifact_contracts.md` |
| Compaction: token-budget strategy enabled in harness | Harness config (`max_context_window_tokens`) |
| Dedupe window — 3-day lookback prevents re-selecting old stories | `config/project.yaml` — `dedupe_window_days: 3` |
| Selection limit — `max_story_cards: 12` caps what enters the synthesis phase | `config/project.yaml` |

### 3. Drift

Root cause: output quality shifts over time; no automated signal.

Controls in this project:

| Control | Where |
|---|---|
| Baseline parity gate — required ≤5%, target ≤1% vs `llm_pipeline` | `tools/baseline_eval.py` — `evaluate_brief_against_index()` |
| Versioned skill files — callers can pin a version | `SKILL.md` — `metadata.version` |
| Evaluation results recorded per run | `day_4/evaluation_results.md` (fill after each run) |
| Loop evaluator — harness re-runs until quality condition passes | Harness `loop_should_continue` predicate |
| `app/index.json` and diagnostics committed to repo | `app/` — stable reference for comparison |

---

## Reflection Loops: Does Each Skill Check Its Own Work?

Yes — by design, via three mechanisms:

1. **Script exit code** — a `scripts/validate.py` in any skill returns exit code 0 (pass) or 1 (fail + reason). The agent interprets the output and either reports success or retries with corrections.

2. **Loop evaluators** — the harness `LoopEvaluators` (or `loop_should_continue` in Python) re-invokes the full agent until a completion predicate is satisfied. Example: `todos_remaining()` keeps the agent running while its todo list has open items.

3. **baseline_eval gate** — after producing a brief, the workflow calls `evaluate_brief_against_index()`. If `required_pass` is False, the workflow can raise or log, blocking the publish step.

---

## Plan / Execute Mode and Context Protection

The harness Plan/Execute mode is a direct mitigation for context rot in multi-step tasks:

- **Plan mode** — interactive, ask clarifying questions, build a todo list, get approval before doing significant work.
- **Execute mode** — autonomous, work through todos independently with no additional context prompting.

This means the agent does not accumulate open-ended conversation history during the heavy lifting — execution starts from a clean, approved plan artifact.

For this project, the equivalent is the `RunState.phase` field in `state.py`:

```
ingest → select → validate → render
```

Each phase transition requires the previous phase's artifact to exist and be valid. Failure in any phase stops the pipeline.
