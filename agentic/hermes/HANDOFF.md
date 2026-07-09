# Agentic Hermes — handoff (pick up here)

**Branch:** `feat/lazy-ingest-eval` (merge via PR)  
**Last updated:** 2026-07-07  
**Status:** Real worker pipeline — research → librarian → synthesizer (`synthesize_digest`) → render. Ready for E2E eval.

---

## Pipeline (one flow)

```
Concierge GO → research × N in parallel (workers + lazy tools)
              → librarian (worker) → synthesizer (worker + synthesize_digest) → grounding / validate / render
```

| Role | Does |
|------|------|
| **Concierge** | `GO` creates kanban graph from `demo_topics` (N research + librarian + synthesizer) |
| **Researcher** | `read_topic_config` → lazy digest tools + Hermes `web_search` → `output.md` |
| **Librarian** | Merges researcher `output.md` files → `librarian.md` |
| **Synthesizer** | Reads `librarian.md` → calls **`synthesize_digest`** → `digest.json` |
| **Pipeline** | Grounding, validate, render (deterministic) |

**No central warm step at GO.** Each digest tool idempotently ensures its slice of
`.preflight/` and `.cache/<prefix>/` on cache miss (or eval fixtures for
`evaluation_test_topic`).

---

## No-bypass policy

The only approved deterministic shortcut is **`evaluation_test_topic`** with
fixtures under `tests/data/evaluation/`. Everything else must complete via Hermes
workers + LLM + tools. Render fails without a valid synthesizer `digest.json`.

Removed / forbidden in production paths:

- `materialize_only` dispatch
- Showcase assembly in `go` / render
- `seed_synthesizer_artifact` / hand-authored stub JSON
- ddgs fallback for unknown registry topics

---

## Commands

| Command | Purpose |
|---------|---------|
| `python agentic/hermes/admin/manage.py bootstrap` | `.runtime` + setup (profiles, ddgs, digest plugin) |
| `python agentic/hermes/admin/manage.py setup` | Deploy SOULs, patches, toolsets (after Hermes upgrade) |
| `python agentic/hermes/admin/manage.py go --fresh` | Full run → report HTML |
| `python agentic/hermes/admin/manage.py verify-handover` | Worker pipeline smoke test (no HTML render) |
| `python agentic/hermes/admin/manage.py dispatch-research` | Research phase only |

**Prereqs:** Hermes on PATH, Ollama at `http://192.168.1.20:11434` with
`qwen3.6:35b`, Hermes gateway running.

---

## E2E test runbook

Run in order before declaring the agentic path green.

### Phase 0 — Offline gates (no LLM, no network)

```bash
cd /path/to/AI_Digest
python -m unittest lib.tests.test_lazy_ingest -v
python run_tests.py   # full suite; synthesizer LLM test needs 4090 up
```

### Phase 1 — Environment preflight

```bash
which hermes
curl -s http://192.168.1.20:11434/api/tags | python3 -c "import sys,json; print('qwen3.6:35b' in [m['name'] for m in json.load(sys.stdin).get('models',[])])"
python agentic/hermes/admin/manage.py status
```

All must succeed. If `setup` was never run on this machine:

```bash
python agentic/hermes/admin/manage.py bootstrap
```

### Phase 2 — Config check

In `agentic/hermes/admin/config/hermes_roles.yaml`:

```yaml
demo_topics:
  - evaluation_test_topic

ollama:
  base_url: http://192.168.1.20:11434/v1
  default_model: qwen3.6:35b
  context_length: 262144

demo_goal:
  max_turns: 50
```

After changing `demo_topics` or `max_turns`, you **must** recreate the board
(`go --fresh`) — existing kanban cards keep their original limits.

### Phase 3 — Full worker E2E (eval topic)

Pick a fresh prefix (UTC timestamp):

```bash
PREFIX="eval$(date -u +%Y%m%d%H%M%S)"
python agentic/hermes/admin/manage.py go --fresh --prefix "$PREFIX"
```

**Expected phases (from `manage.py`):**

| Phase | What happens | Pass signal |
|-------|----------------|-------------|
| A | Research worker(s) → `output.md` | `✓ Phase A: N/N research tasks with valid output.md` |
| B (lib) | Librarian worker → `librarian.md` | `✓ Phase B (librarian): librarian.md passed artifact gate` |
| B (syn) | Synthesizer → `synthesize_digest` → `digest.json` | `✓ Phase B (synthesizer): digest.json passed artifact gate` |
| C | `validate_and_render` | `✓ wrote llm_pipeline/reports/<prefix>.html` |

**Runtime artifacts** (inspect anytime):

```
agentic/hermes/.runtime/artifacts/<prefix>/
├── research/evaluation_test_topic.md
├── librarian.md
├── digest.json
└── handover.json
```

**Report output:**

```
llm_pipeline/reports/<prefix>.html
llm_pipeline/reports/<prefix>.json
```

### Phase 4 — Handover-only smoke (optional, no HTML)

Same worker path but stops before render:

```bash
python agentic/hermes/admin/manage.py verify-handover
```

Pass: `✓ verify-handover PASSED` + board cleared + `handover.json` with provenance trace.

### Phase 5 — Post-run checks

```bash
ls -la "agentic/hermes/.runtime/artifacts/${PREFIX}/"
ls -la "llm_pipeline/reports/${PREFIX}.html"
python -m json.tool "agentic/hermes/.runtime/artifacts/${PREFIX}/digest.json" | head
open "llm_pipeline/reports/${PREFIX}.html"
```

Manual inspect:

- Report loads with 12 categories
- Stories from eval fixtures appear (leaderboard / research / analytics)
- Footer shows release line; JSON has full `generator_version`
- Provenance `(i)` buttons trace to `agent:researcher:*` / `agent:synthesizer:*`

### After E2E — restore production topics

When eval passes, uncomment in `hermes_roles.yaml`:

```yaml
demo_topics:
  - aisearch
  - leaderboard
```

Then `go --fresh` for a live-network production run (longer, needs crawl/API).

---

## Goal-mode turn limit

Kanban tasks created with `--goal` run a **goal loop**: each **turn** is one
model session (plan → tools → judge) until `kanban_complete` or the cap.

| Setting | Where | Default |
|---------|--------|---------|
| Per-task cap | `demo_goal.max_turns` in `hermes_roles.yaml` | 50 |
| Per-turn tool calls | Hermes `agent.max_turns` / env `HERMES_MAX_ITERATIONS` | 90 |

When the cap is hit without `kanban_complete`, Hermes **blocks** the task. Raise
`demo_goal.max_turns` and recreate the board (`go --fresh`) — unblock alone does
not reset the budget.

---

## Key files

| Path | Role |
|------|------|
| `admin/manage.py` | `go`, dispatch, artifact materialization |
| `admin/config/hermes_roles.yaml` | `demo_topics`, Ollama routing, toolsets |
| `admin/config/souls/*.md` | Worker personas (deployed on `setup`) |
| `plugins/digest-tools/` | Lazy ingest + `synthesize_digest` |
| `tools/synthesize.py` | Instructor synthesis implementation |
| `lib/ingest/lazy.py` | `ensure_*` + eval fixture seeding |
| `lib/ingest/topics/registry.py` | Topic → source binding map |
| `tools/artifacts.py` | Artifact gates |
| `docs/ARCHITECTURE.md` | System diagrams (mermaid) |

---

## Not done yet

- Concierge as live Hermes chat profile (`GO` from dashboard/Slack)
- Full `researcher_artifact/v1` / `librarian_artifact/v1` JSON (today: markdown/JSON gates)
- `agentic_enrich` quality pass
- Production E2E with `aisearch` + `leaderboard` on live network
