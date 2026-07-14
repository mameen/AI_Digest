# kaggle_submission.ipynb — Open Issues & Validation Status

_Last updated: 2026-07-14_

## Summary

The notebook is refactored to a real Google ADK agent and is **validated
locally end-to-end**. There is **one open issue on Kaggle**: the kernel dies /
restarts during a run. Root cause is not yet confirmed; the leading suspect is
the mid-session `pip install` in the setup cell (native ABI mismatch).

---

## ✅ Validated locally (in `.venv`, Python 3.12)

- **Packages installed:** `google-adk 2.4.0`, `google-genai 2.11.0`,
  `nest-asyncio 1.6.0`.
- **Live path (`adk-gemini`):** curator called the `fetch_ai_news` FunctionTool,
  fetched 40 live arXiv papers, ranked the top 10; the critic **approved on
  round 1**; schema validation passed (10 cards, ranks 1–10, HTTPS, no dupes).
- **Offline fallback path:** runs clean, emits a valid 10-card `DailyBrief`.
- **Event-loop safety:** `run_adk()` was called from inside an already-running
  asyncio loop (Jupyter-like) via `_build/_test_loop.py` — returned a full
  response with **no hang/crash**. This rules out the `nest_asyncio` /
  `get_event_loop().run_until_complete()` pattern as the crash cause.

## ✅ Fixed

- **API-key loader now surfaces errors.** The old `except Exception: pass`
  silently hid Kaggle Secrets failures and reported "no key". It now prints the
  real error type/message, detects an attached-but-empty secret, and strips
  whitespace. (commit `2a7844d`)
- **Dependencies pinned** in `agentic/kaggle_ai_agents/requirements.txt`:
  `google-adk>=2.4,<3`, `google-genai>=2.11,<3`, `nest-asyncio>=1.6,<2`.

---

## ❌ Open issue #1 — Kaggle kernel dies / restarts

**Symptom (from Kaggle):**

```
Kernel Restarting
The kernel for __notebook_source__.ipynb appears to have died.
It will restart automatically.
```

**Why local tests did not catch it (honest gap):**

| Kaggle | Local run |
|---|---|
| Fresh `pip install google-adk` mid-session, then imports it | Packages already installed — install cell was a no-op |
| Live Jupyter kernel with a running event loop | Plain `python` script (event-loop path separately tested OK) |

A kernel death is a **native crash (segfault/OOM)**, not a Python exception, so
the notebook's `try/except` fallbacks cannot catch it.

**Leading hypothesis:** installing `google-adk` on Kaggle upgrades native deps
(`protobuf` / `grpcio`) while the kernel already has the old versions loaded →
segfault on the next `import google.*`. Classic Kaggle "install → restart".

**Cannot reproduce locally:** the `.venv` already had compatible versions, so
the fresh-install ABI clash never occurs on this machine.

### Needed to confirm

Which cell prints **last** before the restart:
- **Cell 01 (setup)** — right after the `pip install` → confirms ABI/install crash.
- **Cell 05 (agent run)** — first `import google.adk` / agent execution.

### Proposed fix (once confirmed = install crash)

Install once, quietly, at the very top and self-restart so the kernel reloads
the upgraded native libs before any `google.*` import:

```python
import importlib.util, subprocess, sys, os
if importlib.util.find_spec("google.adk") is None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "google-adk", "nest-asyncio"], check=False)
    os.kill(os.getpid(), 9)   # restart; on auto-rerun packages already present
```

On the automatic re-run the package is already present, so it skips the install
and proceeds normally. (`google-genai` is usually preinstalled on Kaggle; drop
it from the install list if so.)

---

## Pre-submission checklist (Kaggle)

- [ ] Attach Secret named exactly `GEMINI_API_KEY` (the working `AQ.` token).
- [ ] After attaching: **Run → Factory reset**, then **Run All** (secrets load
      at session start).
- [ ] **Internet: ON** (arXiv fetch + Gemini calls).
- [ ] Expect cell 01: `✅ Loaded GEMINI_API_KEY from Kaggle Secrets` /
      `LLM path: Gemini (gemini-flash-latest)`.
- [ ] Confirm final output: `via 'adk-gemini' (10 cards)` and schema pass.

## Notes

- Build scaffolding lives in `_build/` (gitignored). Edit sources there and run
  `_build/_build_nb.py` to regenerate the notebook.
- Diagnostic scripts: `_build/_validate_live.py` (full run) and
  `_build/_test_loop.py` (running-loop reproduction).
