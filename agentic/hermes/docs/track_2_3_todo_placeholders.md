# Track 2 → 3 Placeholder Map

**Purpose:** Document every `llm_pipeline.*` import in `agentic/hermes/` that must be replaced with `lib.*` imports once T2 extracts shared libs. These are **NOT stubs** — they are a precise replacement map so T2 work can be wired safely without breaking anything.

**Status:** ⏸️ Blocked on T2 extraction. Zero modules extracted to `lib/` yet.

---

## How to Use This Document

Each section below maps one import source → target location + exact code change needed. When T2 delivers a module, follow the **Replacement** instructions verbatim.

### General Pattern

```python
# BEFORE (current)
from llm_pipeline.editorial import CANONICAL_ORDER, CATEGORY_CATALOG

# AFTER (once lib/ module exists)
from lib.editorial import CANONICAL_ORDER, CATEGORY_CATALOG  # T2 extraction target
```

---

## 1. `llm_pipeline.editorial` — Editorial Brief & Category Catalog

**What it provides:** `load_editorial_brief()`, `CANONICAL_ORDER`, `CATEGORY_CATALOG`, `category_id()`

**Target location:** `lib/editorial.py` (to be created by T2)

### Files Affected (6 files, 8 imports)

#### A. `agentic/hermes/tools/digest_scaffold.py`

```python
# Line 8 — CURRENT:
from llm_pipeline.editorial import CANONICAL_ORDER, CATEGORY_CATALOG

# REPLACEMENT (once lib/editorial.py exists):
from lib.editorial import CANONICAL_ORDER, CATEGORY_CATALOG  # T2 extraction target
```

#### B. `agentic/hermes/tools/enrich.py`

```python
# Line 10 — CURRENT:
from llm_pipeline.editorial import load_editorial_brief

# REPLACEMENT:
from lib.editorial import load_editorial_brief  # T2 extraction target
```

#### C. `agentic/hermes/tools/showcase.py`

```python
# Lines 11-12 — CURRENT:
from llm_pipeline.editorial import CANONICAL_ORDER, CATEGORY_CATALOG, category_id

# REPLACEMENT:
from lib.editorial import CANONICAL_ORDER, CATEGORY_CATALOG, category_id  # T2 extraction target
```

#### D. `agentic/hermes/tools/synthesize.py`

```python
# Lines 12-13 — CURRENT:
from llm_pipeline.editorial import CANONICAL_ORDER, CATEGORY_CATALOG, category_id, load_editorial_brief

# REPLACEMENT:
from lib.editorial import CANONICAL_ORDER, CATEGORY_CATALOG, category_id, load_editorial_brief  # T2 extraction target
```

#### E. `agentic/hermes/tools/topics.py`

```python
# Line 13 — CURRENT:
from llm_pipeline.editorial import CANONICAL_ORDER

# REPLACEMENT:
from lib.editorial import CANONICAL_ORDER  # T2 extraction target
```

---

## 2. `llm_pipeline.validate` — Report Validation

**What it provides:** `validate_digest()`, `apply_validation()`

**Target location:** `lib/validate.py` (to be created by T2)

### Files Affected (3 files, 3 imports)

#### A. `agentic/hermes/tools/publish.py`

```python
# Line 15 — CURRENT:
from llm_pipeline.validate import validate_digest

# REPLACEMENT:
from lib.validate import validate_digest  # T2 extraction target
```

#### B. `agentic/hermes/tools/pipeline_go.py`

```python
# Line 15 — CURRENT:
from llm_pipeline.validate import apply_validation, validate_digest

# REPLACEMENT:
from lib.validate import apply_validation, validate_digest  # T2 extraction target
```

#### C. `agentic/hermes/tools/topics.py`

```python
# Line 15 — CURRENT:
from llm_pipeline.validate import validate_digest

# REPLACEMENT:
from lib.validate import validate_digest  # T2 extraction target
```

---

## 3. `llm_pipeline.enrich` — Digest Enrichment

**What it provides:** `enrich_digest()`

**Target location:** `lib/enrich.py` (to be created by T2)

### Files Affected (2 files, 2 imports)

#### A. `agentic/hermes/tools/baseline.py`

```python
# Line 12 — CURRENT:
from llm_pipeline.enrich import enrich_digest

# REPLACEMENT:
from lib.enrich import enrich_digest  # T2 extraction target
```

#### B. `agentic/hermes/tools/pipeline_go.py`

```python
# Line 11 — CURRENT:
from llm_pipeline.enrich import enrich_digest

# REPLACEMENT:
from lib.enrich import enrich_digest  # T2 extraction target
```

---

## 4. `llm_pipeline.grounding` — Source Grounding

**What it provides:** `collect_roots()`, `find_ungrounded()`, etc.

**Target location:** `lib/grounding.py` (to be created by T2)

### Files Affected (2 files, 2 imports)

#### A. `agentic/hermes/tools/baseline.py`

```python
# Line 13 — CURRENT:
from llm_pipeline.grounding import collect_roots

# REPLACEMENT:
from lib.grounding import collect_roots  # T2 extraction target
```

#### B. `agentic/hermes/tools/topics.py`

```python
# Line 14 — CURRENT:
from llm_pipeline.grounding import collect_roots

# REPLACEMENT:
from lib.grounding import collect_roots  # T2 extraction target
```

---

## 5. `llm_pipeline.history` — Prior Digest History

**What it provides:** `load_prior_digests()`

**Target location:** `lib/history.py` (to be created by T2)

### Files Affected (2 files, 2 imports)

#### A. `agentic/hermes/tools/baseline.py`

```python
# Line 14 — CURRENT:
from llm_pipeline.history import load_prior_digests

# REPLACEMENT:
from lib.history import load_prior_digests  # T2 extraction target
```

#### B. `agentic/hermes/tools/pipeline_go.py`

```python
# Line 13 — CURRENT:
from llm_pipeline.history import load_prior_digests

# REPLACEMENT:
from lib.history import load_prior_digests  # T2 extraction target
```

---

## 6. `llm_pipeline.diagnostics` — Run Instrumentation

**What it provides:** `init_collector()`, `get_collector()`, `finish_collector()`, `log()`, `instrumented_llm_call()`, `_render_run_log()`, `_render_waterfall_html()`

**Target location:** `lib/diagnostics.py` (to be created by T2)

### Files Affected (3 files, 5 imports)

#### A. `agentic/hermes/admin/manage.py`

```python
# Line 1503 — CURRENT:
from llm_pipeline.diagnostics import init_collector

# REPLACEMENT:
from lib.diagnostics import init_collector  # T2 extraction target

# Line 1514 — CURRENT:
from llm_pipeline import diagnostics as diag_mod

# REPLACEMENT:
import lib.diagnostics as diag_mod  # T2 extraction target
```

#### B. `agentic/hermes/tools/agent_diagnostics.py`

```python
# Lines 167-168 — CURRENT:
from llm_pipeline.diagnostics import get_collector
from llm_pipeline.environment import capture_environment, enrich_diagnostics_report

# REPLACEMENT (also needs lib/environment.py):
from lib.diagnostics import get_collector  # T2 extraction target
from lib.environment import capture_environment, enrich_diagnostics_report  # T2 extraction target
```

#### C. `agentic/hermes/tools/pipeline_go.py`

```python
# Line 10 — CURRENT:
from llm_pipeline.diagnostics import finish_collector, get_collector, init_collector, log

# REPLACEMENT:
from lib.diagnostics import finish_collector, get_collector, init_collector, log  # T2 extraction target
```

---

## 7. `llm_pipeline.llm_client` — LLM Client Factory

**What it provides:** `make_client()`, `make_raw_chat()`

**Target location:** `lib/llm_client.py` (to be created by T2)

### Files Affected (2 files, 2 imports)

#### A. `agentic/hermes/tools/enrich.py`

```python
# Line 11 — CURRENT:
from llm_pipeline.llm_client import make_client, make_raw_chat

# REPLACEMENT:
from lib.llm_client import make_client, make_raw_chat  # T2 extraction target
```

#### B. `agentic/hermes/tools/synthesize.py`

```python
# Line 13 — CURRENT:
from llm_pipeline.llm_client import make_client

# REPLACEMENT:
from lib.llm_client import make_client  # T2 extraction target
```

---

## 8. `llm_pipeline.environment` — Environment Capture

**What it provides:** `capture_environment()`, `enrich_diagnostics_report()`, `format_env_line()`, `format_net_line()`, `hw_metric_cards()`, `summarize_network()`

**Target location:** `lib/environment.py` (to be created by T2)

### Files Affected (1 file, 1 import)

#### A. `agentic/hermes/tools/agent_diagnostics.py`

```python
# Line 168 — CURRENT:
from llm_pipeline.environment import capture_environment, enrich_diagnostics_report

# REPLACEMENT:
from lib.environment import capture_environment, enrich_diagnostics_report  # T2 extraction target
```

---

## 9. `llm_pipeline.render` — Report Rendering

**What it provides:** `render()`, `rebuild_reports_archive()`

**Target location:** `lib/render.py` (to be created by T2)

### Files Affected (1 file, 1 import)

#### A. `agentic/hermes/tools/baseline.py`

```python
# Line 15 — CURRENT:
from llm_pipeline.render import render

# REPLACEMENT:
from lib.render import render  # T2 extraction target
```

---

## 10. `llm_pipeline.diagnostics_frame` — Diagnostics HTML Frames

**What it provides:** `rebuild_diagnostics_archive()`

**Target location:** `lib/diagnostics_frame.py` (to be created by T2)

### Files Affected (1 file, 1 import)

#### A. `agentic/hermes/tools/agent_diagnostics.py`

```python
# Line 236 — CURRENT:
from llm_pipeline.diagnostics_frame import rebuild_diagnostics_archive

# REPLACEMENT:
from lib.diagnostics_frame import rebuild_diagnostics_archive  # T2 extraction target
```

---

## 11. Test File Imports

### `agentic/hermes/tests/test_board_topics.py`

```python
# Line 25 — CURRENT:
from llm_pipeline.validate import validate_digest  # noqa: E402

# REPLACEMENT:
from lib.validate import validate_digest  # T2 extraction target
```

---

## Summary Table

| Import Source | Target in `lib/` | Files Affected | Total Imports |
|---|---|---|---|
| `llm_pipeline.editorial` | `lib/editorial.py` | 5 files | 6 |
| `llm_pipeline.validate` | `lib/validate.py` | 3 files | 3 |
| `llm_pipeline.enrich` | `lib/enrich.py` | 2 files | 2 |
| `llm_pipeline.grounding` | `lib/grounding.py` | 2 files | 2 |
| `llm_pipeline.history` | `lib/history.py` | 2 files | 2 |
| `llm_pipeline.diagnostics` | `lib/diagnostics.py` | 3 files | 5 |
| `llm_pipeline.llm_client` | `lib/llm_client.py` | 2 files | 2 |
| `llm_pipeline.environment` | `lib/environment.py` | 1 file | 1 |
| `llm_pipeline.render` | `lib/render.py` | 1 file | 1 |
| `llm_pipeline.diagnostics_frame` | `lib/diagnostics_frame.py` | 1 file | 1 |
| **Total** | **10 modules** | **12 files** | **32 imports** |

---

## Safety Checklist for T2 → T3 Wiring

When wiring each replacement, verify:

1. **API compatibility:** The `lib/` module exports the same function signatures as the `llm_pipeline/` source
2. **No circular deps:** `lib/` modules don't import from `agentic/hermes/`
3. **Test coverage:** All existing tests pass after the swap (run `python run_tests.py`)
4. **No side effects:** The `lib/` module doesn't have different default behavior (e.g., different config paths)
5. **Update docstrings:** Replace any `llm_pipeline/` references in docstrings with `lib/`

---

## What's Already Done (T3-D)

The following imports are **already wired** to `lib/hermes/` and need no further action:

| Module | Status |
|---|---|
| `lib.hermes.skills_provider` | ✅ Wired — SkillsProvider, SkillEntry |
| `lib.hermes.artifacts` | ✅ Wired — validate_researcher_artifact, validate_librarian_artifact, validate_synthesizer_artifact |
| `lib.hermes.runtime_store` | ✅ Wired — run_dir, persist_*, load_* |

These are **Hermes-specific** adapters that live in `lib/hermes/`. The remaining 32 imports above are **shared pipeline logic** that T2 must extract from `llm_pipeline/` → `lib/` (not `lib/hermes/`).
