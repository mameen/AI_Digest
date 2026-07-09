# Manual Hermes bootstrap (learn by doing)

Hands-on path through upstream Hermes **before** using
`python agentic/hermes/admin/manage.py setup`. After you understand the pieces,
automate with `bootstrap` + `setup`.

**Model default (laptop):** `llama3.1:latest` (~5 GB, **128K** context). Hermes
requires **≥64K native context** — `qwen2.5:7b` (32K) is rejected even if the
Ollama app slider is at 64k. Upgrade showcase runs to `qwen3.6:35b` on a beefier
GPU — see [ADR-001](docs/adr/001-local-ollama-with-per-role-model-routing.md).

Each section has **Terminal** and **Web** paths. Web steps use the **browser
admin** opened in §0 — left nav with **Profiles**, **Config**, **Skills**,
**System**, **Kanban**, etc.

**Profile switcher (web)** — sidebar, above nav links (only when **two or more**
profiles exist). Dropdown: *this dashboard (default)* or the profile name.
Banner: *Managing profile “…”* when configuring another profile. With only
`default`, you are already on it until you create more profiles.

---

## Concepts (read once)

| Term | What it is |
|---|---|
| **Profile** | A named agent *role* (`concierge`, `researcher`, …) with its own model, tools, and `~/.hermes/profiles/<name>/` dir. Not a person and not a topic. |
| **Session** | One chat thread (messages + tool calls). `hermes chat` starts a new session unless you `--resume`. |
| **Gateway** | Background service for Slack/cron/webhooks. Browser chat + kanban dispatch can work without it; long-running board workers need a dispatcher (dashboard or gateway). |
| **Kanban** | SQLite task board — fan-out research tasks, blocked synthesizer, worker PIDs, heartbeats. |
| **Dispatcher** | Picks `ready` tasks, spawns `hermes -p <profile> chat -q "work kanban task …"`. Cap parallelism on a laptop (`dispatch --max 1`). |
| **Toolset** | Which tools a profile may call (`terminal`, `web`, `kanban`, …). Kanban task *creation* needs `kanban` in toolsets. |

---

## 0. Prerequisites

**Terminal**

```bash
ollama list                    # need llama3.1:latest (or: ollama pull llama3.1)
which hermes                   # upstream Hermes CLI on PATH
cd /path/to/AI_Digest
python admin/manage.py bootstrap --skip-doctor   # repo .venv + pipeline only
```

**Web** — open the admin dashboard **once** before any Web steps below:

```bash
python agentic/hermes/admin/manage.py hermes dashboard
```

Leave the browser tab open for §1–8.

---

## 1. Point Hermes at Ollama (default profile)

Target the **`default`** profile.

**Terminal**

```bash
hermes config set model.default llama3.1:latest
hermes config set model.provider custom
hermes config set model.base_url http://localhost:11434/v1
hermes config set model.context_length 131072
hermes doctor
```

**Web**

1. Profile switcher → **`default`**.
2. **Models** → set default to **`llama3.1:latest`**.
3. **Config** → **model** section → `provider` = `custom`, `base_url` = `http://localhost:11434/v1`, `context_length` = `131072`.
4. **System** → **Run doctor**.

First-time alternative: `hermes setup model` (terminal wizard).

**Check:** doctor green; `hermes profile list` shows `default` → `llama3.1:latest`.
In the web UI, **Profiles** lists `default` with that model.

---

## 2. Smoke-test chat (Phase 1)

**Terminal**

```bash
hermes chat -q "Reply in one sentence — which Ollama model are you using?"
```

**Web** — **Chat** tab, profile **`default`**, same question.

**Pass:** one short reply, no API-key errors.

---

## 3. Enable kanban toolset

**Terminal**

```bash
hermes config set toolsets '["hermes-cli","kanban"]'
```

**Web** — **Skills** → **Toolsets** tab → enable **`kanban`** (keep **`hermes-cli`** on).

Without `kanban`, the agent cannot create board tasks from chat.

---

## 3b. Web search + digest tools (free, no API keys)

**Automated by `setup` / `bootstrap`:** `web.backend ddgs`, `hermes tools post-setup ddgs`,
doctor web check, and a **kanban goal-mode patch** (adds `--quiet` to goal workers —
upstream spawns `-q` only, so the Ralph loop never ran without this).

After setup, **restart the gateway** so the dispatcher picks up the patch:

```bash
hermes gateway restart
```

**One-time per machine** — symlink the digest plugin (not done by bootstrap):

```bash
REPO=/path/to/AI_Digest
ln -sf "$REPO/agentic/hermes/plugins/digest-tools" ~/.hermes/plugins/digest-tools
```

Restart the gateway after linking. `setup` enables toolset **`digest`** on the
`researcher` profile (`verify_url`). Search uses Hermes built-in **`web_search`**
via ddgs.

**Terminal verify**

```bash
hermes doctor | grep -i web
hermes -p researcher config show | grep toolsets
```

**Web** — **System → Run doctor** (web row green); **Profiles → researcher →
Toolsets** → **`digest`** on.

---

## 4. Create digest role profiles (one-time)

Role text lives in
[`admin/config/hermes_roles.yaml`](admin/config/hermes_roles.yaml).
Create four roles — **not** one profile per topic (no `researcher-aisearch`).

### What `hermes profile create concierge --clone-from default --description "…"` means

| Piece | Meaning |
|---|---|
| **`profile create concierge`** | Adds a new agent **role** named `concierge`. Hermes creates `~/.hermes/profiles/concierge/` with its own config, memory, and sessions. You can run `hermes -p concierge chat` or pick `concierge` in the profile switcher. |
| **`--clone-from default`** | Copy **settings** from `default` (Ollama URL, model, toolsets, API layout) — not chat history. New profile starts with fresh memory/sessions but same “wiring” as `default`. |
| **`--description "…"`** | One-line **job description** for the kanban orchestrator: when a task is assigned to `concierge`, Hermes uses this text to understand the role (not just the profile name). Same as “what is this profile good at?” in the web UI. |

You are **not** creating a user, a Slack account, or a digest category — only a
**reusable hat** the dispatcher can wear.

### SOUL.md — deployed by `setup`

Repo templates live in [`admin/config/souls/`](admin/config/souls/). **`setup` /
`bootstrap` copies each to `~/.hermes/profiles/<role>/SOUL.md`** (overwrites).

| File | Role |
|---|---|
| `concierge.md` | Front desk, GO → kanban graph |
| `researcher.md` | Kanban worker + `kanban_complete` protocol |
| `librarian.md` | Merge/classify fan-in |
| `synthesizer.md` | Final digest from librarian |

`--description` on `profile create` is still for kanban routing; **SOUL.md** is
the chat/worker persona. Edit templates in git, re-run `setup` to push.

**Terminal** — run four times (descriptions match our digest roles):

```bash
hermes profile create concierge --clone-from default \
  --description "AI Digest front desk: topics, schedule, GO intent only."

hermes profile create researcher --clone-from default \
  --description "One digest target per task; fetch and summarize; researcher_artifact."

hermes profile create librarian --clone-from default \
  --description "Merge researcher artifacts; taxonomy and knowledge graph."

hermes profile create synthesizer --clone-from default \
  --description "Compose final digest from librarian output."

hermes profile list
```

**Web** — **Profiles** → **New profile** → for each role:

- **Name** → role name (lowercase).
- **Clone config from** → **`default`**.
- **Description** → same text as CLI above.
- **Model** → inherit from clone / default.

All profiles use **`llama3.1:latest`** on a laptop (single model in VRAM).

---

## 5. Kanban POC (Phase 2) — **research × N → librarian → synthesizer**

This is the **AI Digest** task graph — not the shortened Hermes video demo (which
skipped librarian). One `researcher` profile handles every topic; add topics in
[`admin/config/hermes_roles.yaml`](admin/config/hermes_roles.yaml) `demo_topics`
as you add sources.

```
research_aisearch  ─┐
research_robotics  ─┤
research_llm       ─┼──→ librarian ──→ synthesizer
research_rag       ─┘
```

**Do not** run four parallel workers on a laptop — cap at one:

```bash
hermes config set kanban.max_in_progress 1
hermes gateway start    # once — auto-dispatch
```

**Terminal** — create the board (correct parent links, `--goal` Ralph loop, no chat guessing):

```bash
python agentic/hermes/admin/manage.py demo-board
hermes kanban list
hermes kanban dispatch --max 1    # repeat while tasks sit in ready
```

Cards are created with **`--goal`** so workers stay in-session until
`kanban_complete` (see `demo_goal` in `hermes_roles.yaml`).

**Web** — open dashboard (§0), **Kanban** tab to watch lanes. **Nudge dispatcher**
if needed.

**Pass:** researchers finish → **librarian** promotes → librarian finishes →
**synthesizer** promotes. (Worker quality on `llama3.1` may still need a stronger
model or SOUL tuning — the graph is what we're proving.)

**Stop if the machine heats up**

```bash
pkill -f "work kanban task"
hermes kanban reclaim <task_id>    # per stuck running task
ollama stop llama3.1:latest
```

In the web UI: **Kanban** → stuck card → reclaim / complete / archive if offered.

---

## 6. Inspect state (debugging)

| What | Terminal | Web |
|---|---|---|
| Task list | `hermes kanban list` | **Kanban** → board columns |
| Task detail | `hermes kanban show <task_id>` | **Kanban** → click a card |
| Chat threads | `hermes sessions list` | **Sessions** |
| Profile config | `hermes profile show researcher` | **Profiles** → `researcher` |

Worker artifacts: `~/.hermes/kanban/workspaces/<task_id>/`

---

## 7. Clean slate (nuke Hermes experiment)

**Terminal**

```bash
# archive + purge kanban tasks on default board
hermes kanban archive t_xxx t_yyy ...   # all task ids from `kanban list`
hermes kanban archive --rm t_xxx ...    # purge archived

# remove digest profiles (keep default)
hermes profile delete concierge -y
hermes profile delete researcher -y
hermes profile delete librarian -y
hermes profile delete synthesizer -y

# repo agent runtime only
python agentic/hermes/admin/manage.py nuke --yes
```

**Web**

1. **Kanban** → select tasks → **Archive** (purge archived if offered).
2. **Profiles** → each digest role → **Delete** (confirm). Keep **`default`**.
3. Repo-only: `python agentic/hermes/admin/manage.py nuke --yes` (no web equivalent).

`~/.hermes/` (global Hermes home) is **not** deleted — only profiles/tasks you remove.

---

## 8. When ready — automate

**Terminal**

```bash
python agentic/hermes/admin/manage.py setup      # Ollama, profiles, SOUL, ddgs, researcher digest toolset
python agentic/hermes/admin/manage.py bootstrap  # .runtime + setup

# One-time: ln -sf "$REPO/agentic/hermes/plugins/digest-tools" ~/.hermes/plugins/digest-tools
```

**Web** — after `setup`, check **Profiles** and **System → Run doctor**.

---

## Related

- [POC.md](POC.md) — phased proof checklist
- [system_roles.md](system_roles.md) — who does what
- [slack.md](slack.md) — gateway + Slack (Phase 3)
- [admin/README.md](admin/README.md) — agentic Hermes admin
- [../../../admin/README.md](../../../admin/README.md) — pipeline admin
- [Hermes profiles docs](https://hermes-agent.nousresearch.com/docs/user-guide/profiles) — upstream reference
