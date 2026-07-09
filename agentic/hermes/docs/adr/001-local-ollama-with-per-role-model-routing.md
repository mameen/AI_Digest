# ADR-001: Local Ollama default with per-role model routing

**Status:** Accepted  
**Date:** 2026-07-05  
**Scope:** `agentic/hermes`, `config.yaml`, optional upstream Hermes integration  

**Related:**

- [`../system_roles.md`](../../system_roles.md)
- [`../working_agreements.md`](../../working_agreements.md)
- [`../202607_research/hermes-parallel-agents-walkthrough.md`](../202607_research/hermes-parallel-agents-walkthrough.md)

---

## Context

AI Digest must stay **local-first and low cost** for day-to-day development and
showcase runs (Ollama on a workstation, no standing cloud bill). The agentic
Hermes track adds multiple roles (Concierge, Researcher, Librarian, Author) with
different cognitive loads — fetch/summarize vs taxonomy/graph vs executive
compose.

We also want the option to adopt **upstream Hermes** (NousResearch) for
kanban/Telegram orchestration, which is **CLI- and profile-driven**. The design
must not lock every role to one model or one provider when a paid tier would
earn its keep (speed for researchers, reasoning for librarian/author).

Constraints:

- Portfolio project — predictable cost, reproducible local runs
- Existing `llm_pipeline` already uses `config.yaml` → `llm.provider: ollama`
- Roles already specify model **tier** (fast vs smart) in `system_roles.md`
- Future: swap individual roles to cloud models without rewriting orchestration

---

## Decision

### 1. Default: local Ollama for all roles

Ship with **one local stack** as default — same philosophy as `llm_pipeline`.

**Two tiers** (pick in `config.yaml` → `llm.model`):

| Tier | Model | VRAM | When |
|---|---|---|---|
| **Dev / laptop** (default) | `llama3.1:latest` | ~5 GB, **128K** ctx | Hermes POC, agentic dev, pipeline on MacBook |
| **Showcase** (upgrade) | `qwen3.6:35b` | ~24 GB | RTX 4090-class; published digest quality |

```yaml
# config.yaml
llm:
  provider: ollama
  model: llama3.1:latest      # dev default; upgrade to qwen3.6:35b when VRAM allows
  base_url: http://localhost:11434/v1
```

**Hermes constraint:** upstream Hermes Agent rejects models with **< 64K native
context** (e.g. `qwen2.5:7b` is 32K — fine for `run.py`, not for Hermes chat).
The Ollama app “context length” slider does not change the model card Hermes reads.

No cloud keys required to develop or demo the agentic path.

### 2. Per-role model routing in config (open override)

Add an **`agentic.models`** block that maps **role profile → model endpoint**.
Each entry can override provider, model, base URL, and optional tags for
requirements (speed, accuracy, reasoning):

```yaml
agentic:
  enabled: false              # flip when Hermes runner lands
  models:
    default:                  # fallback when role omitted
      provider: ollama
      model: llama3.1:latest
      base_url: http://localhost:11434/v1
    concierge:
      provider: ollama
      model: llama3.1:latest
      requirements: [reasoning, intent_parsing]
    researcher:
      provider: ollama
      model: llama3.1:latest
      requirements: [speed, cost]
    librarian:
      provider: ollama
      model: llama3.1:latest
      requirements: [reasoning, taxonomy]
    synthesizer:
      provider: ollama
      model: llama3.1:latest
      requirements: [reasoning, prose, accuracy]
    # Showcase: qwen3.6:35b for all roles when VRAM allows
```

**Resolution order:** `agentic.models.<role>` → `agentic.models.default` →
top-level `llm.*`.

Orchestrator code resolves the model at **task dispatch**, not hard-coded in
prompts. Roles stay profile names; subjects stay task descriptions.

### 3. Two configuration surfaces (both CLI-capable)

We distinguish **upstream Hermes the product** from **AI Digest agentic runner**:

| Surface | When | How configured |
|---|---|---|
| **Upstream Hermes** | Docker/VPS kanban, Telegram, gateway | `hermes` CLI — profiles, `config set`, gateway |
| **AI Digest agentic** | In-repo Python runner, A/B vs `llm_pipeline` | Repo `config.yaml` + future `run_hermes.py` CLI |

Both can coexist: Hermes profiles for orchestration *or* pure Python for local
dev — same role names, same model routing schema in repo config.

### 4. Upstream Hermes CLI (reference — not required for local dev)

If/when we deploy [NousResearch Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/profiles):

| Task | CLI |
|---|---|
| Create role profile | `hermes profile create researcher --description "…"` |
| Set model per profile | `researcher config set model.default <provider/model>` |
| Switch active profile | `hermes -p researcher …` or `hermes profile use researcher` |
| Add toolset (kanban) | Edit profile `config.yaml` or `hermes config set …` |
| Gateway / cron | `researcher gateway start`, cron via chat or config |

Each profile = isolated `HERMES_HOME` with its own `config.yaml`, `.env`, memory,
skills, gateway. Maps 1:1 to our roles: `concierge`, `researcher`, `librarian`,
`synthesizer` (Author).

**AI Digest default path does not require Hermes installed** — document CLI for
operators who want full kanban/Telegram; implement `run_hermes.py` for
zero-extra-cost local iteration.

### 5. Planned AI Digest CLI (`run_hermes.py`)

In-repo CLI mirrors familiar patterns without Hermes dependency:

```bash
# future
python -m agentic.hermes.run --doctor          # Ollama + role models reachable
python -m agentic.hermes.run --go --start …    # fan-out run
python -m agentic.hermes.run config show       # resolved models per role
python -m agentic.hermes.run config set researcher.model llama3.1:latest
```

Reads/writes `config.yaml` `agentic.models` — same source of truth whether
runner is Python or Hermes-backed.

### 6. Cloud upgrade path (future, opt-in)

When budget allows, change **one role** without touching others:

```yaml
agentic:
  models:
    researcher:
      provider: ollama
      model: llama3.1:latest
    synthesizer:
      provider: openai          # example
      model: gpt-4.1
      base_url: https://api.openai.com/v1
      # keys via .env — never committed
```

Requirements tags (`speed`, `reasoning`, …) are **documentation and tooling
hints** for `config show` / doctor — not auto-routing to cloud in v1.

---

## Consequences

### Positive

- **$0 default** — local Ollama only for development and showcase
- **Role-tier alignment** — fast researchers, smart librarian/author when configured
- **Gradual spend** — upgrade one role/provider at a time
- **Hermes-compatible** — can map each role to a Hermes profile + CLI if desired
- **A/B friendly** — same `config.yaml` feeds `llm_pipeline` baseline and agentic runs

### Negative / tradeoffs

- **Multiple small models** on one GPU may contend — doctor should warn on VRAM
- **Two config paths** (Hermes profiles vs repo YAML) need docs to avoid drift
- **Schema not implemented yet** — ADR accepted before `agentic.models` code lands

### Follow-ups

- [ ] Add `agentic.models` to `config.yaml` (disabled by default)
- [ ] `run_hermes.py config show|set|doctor`
- [ ] Model resolver in agentic runner (role → client, like `llm_client.make_client`)
- [ ] Document Hermes profile setup in `docs/ops/hermes-profiles.md` if we adopt Docker path

---

## Alternatives considered

| Option | Why not (for now) |
|---|---|
| Single model for all roles | Simple but slow (parallel researchers on 35B) or dumb (7B synthesizer) |
| Cloud-first | Standing cost; conflicts with local-first portfolio story |
| Hard-code models in profile YAML only | Works for Hermes path but splits truth from `config.yaml` |
| Auto-select cloud by `requirements` tags | Magic routing, cost surprises — defer to explicit config |
| MCP for model selection | Wrong layer; models are runtime config, not external tool |

---

## Summary

**Yes — Hermes (the product) is configured through the CLI** (`hermes profile`,
`hermes config set`, per-profile aliases). **AI Digest agentic** will use repo
`config.yaml` + a thin CLI, with optional Hermes profiles for the same four
roles. **Default everything to local Ollama**; override per role when speed,
accuracy, or reasoning justify a different model or provider.
