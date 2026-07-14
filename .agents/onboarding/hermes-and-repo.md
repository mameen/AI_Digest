# Hermes profiles & repo onboarding (ORIO crew)

> **Audience:** `orio_concierge`, `orio_researcher`, `orio_librarian`, `orio_synthesizer`.
> **Maintainers:** update this file when import wiring, hooks, env, or role boundaries change.
> **Human rulebook:** [`.agents/AGENTS.md`](../AGENTS.md) · **Hermes admin:** [`agentic/hermes/admin/README.md`](../../agentic/hermes/admin/README.md)

Every ORIO profile should **`read_file` this document** when the user asks about imports,
environment, git, commits, PII, or “how the repo works” — do not guess from generic Python
packaging rules.

**Paths:** repo root `.agents/onboarding/hermes-and-repo.md` · after `manage.py setup`, a copy
lives at `~/.hermes/profiles/<orio_*>/REPO_ONBOARDING.md` (same content).

---

## Repo layout (what matters to agents)

| Path | Purpose |
|---|---|
| `agentic/hermes/tools/` | Python adapters loaded as `tools.*` under Hermes (see imports below) |
| `agentic/hermes/plugins/digest-tools/` | Hermes plugin — registers `digest_*` and ingest tools |
| `agentic/hermes/admin/manage.py` | Production GO, setup, render-from-board |
| `agentic/hermes/.runtime/` | Kanban-adjacent state; **gitignored** (artifacts survive workspace wipe) |
| `agentic/hermes/reports/`, `diagnostics/` | Agentic HTML/JSON outputs (tracked) |
| `app/` | GitHub Pages deploy tree (after `digest_deploy_app`) |
| `.agents/` | Contributor + agent onboarding (this file) |
| `lib/`, `llm_pipeline/` | Shared ingest, validate, render |
| `.cache/` | Ingest prefetch — **gitignored** |

Repo root is the AI Digest clone (where `run.py` and `config.yaml` live).

---

## How `tools.*` imports work under Hermes (read this before diagnosing import errors)

**Common mistake:** “`tools/` has no package / needs PYTHONPATH / `manage.py setup` pip-installs it.”

**Actual mechanism:**

1. Upstream **Hermes** already owns a top-level `tools` package.
2. Our **`digest-tools`** plugin loads repo modules with **`_overlay_agentic_tool()`** in
   `agentic/hermes/plugins/digest-tools/__init__.py` — it registers
   `agentic/hermes/tools/<name>.py` into `sys.modules` as `tools.<name>`.
3. Dependencies are preloaded (e.g. `orchestration` → `profiles`, `artifacts`, `runtime_store`).
4. `agentic/hermes/tools/__init__.py` **exists** (may be empty); overlay does **not** rely on
   pip install or `PYTHONPATH`.

**`manage.py`** adds `agentic/hermes` to `sys.path` and imports normally — that path works
without the overlay.

**After changing** `agentic/hermes/tools/*.py`, plugin deps, SOULs, or kanban patches:

```bash
python agentic/hermes/admin/manage.py setup
hermes gateway restart
```

Re-open the dashboard tab if it was already open. **Send a new Concierge message**
after restart — a long chat turn may remember an old tool error.

**SOUL vs plugin code:** `setup` copies SOULs to `~/.hermes/profiles/`. The
`digest-tools` plugin is symlinked from the repo — Python still **caches imported
modules in the gateway process** until restart. Fixing `tools.runtime_store` on disk
does nothing for Concierge until the gateway reimports the plugin.

---

## Environment & requirements

| Step | Command | When |
|---|---|---|
| Python venv + deps | `python admin/manage.py bootstrap` | Once per clone / after dep changes |
| Hermes profiles + plugin | `python agentic/hermes/admin/manage.py setup` | After SOUL/tool/patch changes |
| Gateway | `hermes gateway start` (first time) · `hermes gateway restart` (after setup) | Before GO / Concierge tools |
| Chat UI | `python agentic/hermes/admin/manage.py hermes dashboard` | Manual verification |
| Ollama | Running with model from `config.yaml` / `hermes_roles.yaml` | All LLM roles |
| Hermes CLI | `hermes` on PATH | Kanban + gateway |

**Tests (maintainers):** `python run_tests.py` — Python unittest + Node widget tests; prefer
real fixtures, not mocks (see `.agents/AGENTS.md`).

**Production GO:** `python agentic/hermes/admin/manage.py go --start YYYY-MM-DD --fresh`  
Concierge equivalent: `digest_go` (subprocess of the same command).

---

## Secrets and commit policy

Commits are **maintainer-only** attribution. Pre-commit hooks (`.githooks/`) run on staged files:

1. `scripts/audit_secrets.py --staged` — Gitleaks / detect-secrets

| File | Purpose |
|---|---|
| `.gitleaksignore` | Secret scanner allowlist |
| `.secrets.baseline` | detect-secrets baseline |

**Never commit:** API keys, `.env`, credentials, unrelated personal data in source or tests.
**Gitignored but sensitive:** `.cache/`, `agentic/hermes/.runtime/`, `.kb/` — do not stage even
if hooks sometimes allow via ignore rules.

**Agent rule:** do not paste maintainer home paths, tokens, or personal identifiers into
kanban comments, artifacts, or chat. Use run prefix and role names only.

Manual audit: `python scripts/audit_secrets.py --all`

Full hook install: see [`.githooks/README.md`](../../.githooks/README.md).

---

## Git — what each role may assume

| Role | Git access |
|---|---|
| **Concierge** | **`digest_publish` only** — stages fixed deploy paths, `git commit`, optional `git push origin/main` with `confirm_push: true` after explicit user approval. **No** `git status`, branches, merge, or diff tools. |
| **Workers** | Write artifacts in kanban workspace / `.runtime/artifacts/` — **no** git tools. |
| **Maintainers** | Full git outside Hermes; work on branches; `main` is protected; push only when intended. |

Concierge **does not know** the current branch unless told. “Sync the file” or “push the fix”
means: maintainer checks out the right branch locally, merges, runs `setup`, restarts gateway.

**Versioning:** release line `MAJOR.MINOR` in `pipeline/__init__.py` only — do not bump unless
maintainer asks. Run prefix (`YYYYMMDDHHmmss`) is the build segment per report.

---

## Role boundaries (quick)

| Profile | Reads | Does not |
|---|---|---|
| `orio_concierge` | `digest_board_status`, pipeline tools | Fetch URLs, write digest prose, arbitrary git |
| `orio_researcher` | Task target, ingest tools, workspace | Merge topics, write digest |
| `orio_librarian` | Researcher `output.md`, standing topics | Fetch new URLs, final HTML |
| `orio_synthesizer` | `librarian.md`, `synthesize_digest` | Render, validate, re-fetch, raw researcher files |

Post-kanban **render** is `manage.py go` Phase C — not a kanban task. See Concierge SOUL
`pipeline_process` / `digest_board_status` JSON.

---

## Further reading

| Topic | Doc |
|---|---|
| Day-to-day rules | [`.agents/AGENTS.md`](../AGENTS.md) |
| Architecture | [`onboarding/architecture.md`](architecture.md) |
| Run / redeploy | [`onboarding/running-and-tooling.md`](running-and-tooling.md) |
| Debug / pitfalls | [`onboarding/debugging-and-pitfalls.md`](debugging-and-pitfalls.md) |
| ORIO roles | [`agentic/hermes/system_roles.md`](../../agentic/hermes/system_roles.md) |

When this doc and another conflict on **product story**, root [`README.md`](../../README.md) wins.
When this doc and `AGENTS.md` conflict on **agent workflow**, `AGENTS.md` wins.
