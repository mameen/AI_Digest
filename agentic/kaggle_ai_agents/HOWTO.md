# How-To Guide

Quick reference for common tasks in this project.

---

## Assessment: People & LLMs Required to Run & Evaluate the PoC

Before starting, assess your team and infrastructure against these requirements.

### 👥 People & Skills

**Essential (Required)**
| Role | Skills | Time Investment | Notes |
|------|--------|-----------------|-------|
| **Python Developer** | Python 3.11+, pytest, CLI, Git | 2-4 hours | Runs tests, executes workflows, troubleshoots |
| **QA / Test Verifier** | Can read JSON, compare outputs, verify schema | 1-2 hours | Validates brief schema, checks evaluation results |

**Recommended**
| Role | Skills | Time Investment | Notes |
|------|--------|-----------------|-------|
| **DevOps / Infra** | Docker (optional), environment setup | 30min | Helps with Ollama setup if LLM backend chosen |
| **LLM Researcher** | Prompt engineering, LLM evaluation | 1-2 hours | Needed only if using Ollama backend for experimentation |

**Optional**
| Role | Skills | Time Investment | Notes |
|------|--------|-----------------|-------|
| **Project Manager** | Task tracking, timeline coordination | 30min | Helps with multi-day execution planning |
| **Data Analyst** | Can assess quality of news stories ranked | 1-2 hours | Subjective evaluation of brief quality |

---

### 🤖 LLM & Infrastructure Assessment

#### Backend Comparison & Requirements

| Backend | LLM Needed | Setup Time | Cost | Network | Quality |
|---------|-----------|-----------|------|---------|---------|
| **direct_script** | None | 0 | Free | Local only | Deterministic (keyword-based) |
| **google_adk** | (Optional future) | 5min | Free | Local only | Deterministic (instruction-based) |
| **ollama** | Yes (llama2/mistral) | 20-30min | Free (local) | Local only | LLM-based (experimental) |

#### Choose Your Backend

**Starter (No LLM, ~2 hours total)**
```yaml
# config/project.yaml
agent:
  backend: "direct_script"
```
- No external dependencies
- Deterministic results (good for testing)
- Fast (~1 min with stubs, ~5 min with real sources)
- Best for: CI/CD, initial validation

**Standard (Course-Aligned, ~2-3 hours total)**
```yaml
# config/project.yaml
agent:
  backend: "google_adk"
```
- No LLM required (deterministic orchestration)
- Instruction-driven agent (follows course design)
- Medium speed (~6-10 min with real sources)
- Best for: Production use, course demonstration

**Advanced (LLM-Based, ~3-4 hours total)**
```yaml
# config/project.yaml
agent:
  backend: "ollama"
```
- Requires local Ollama + LLM model (~10min setup, 4-5GB disk)
- LLM-based ranking (experimental)
- Slower (~10-15 min with real sources)
- Best for: Research, fine-tuning ranking, experimentation

---

### ✅ Pre-Flight Checklist

Before running the full PoC:

- [ ] **Python 3.11+ installed** 
  ```bash
  python3 --version
  # Should show 3.11.x or later
  ```

- [ ] **Repository cloned and dependencies installed**
  ```bash
  pip install -r agentic/kaggle_ai_agents/requirements.txt
  pip install -r agentic/kaggle_ai_agents/requirements-dev.txt
  ```

- [ ] **Tests pass locally** 
  ```bash
  PYTHONPATH=agentic/kaggle_ai_agents/src python -m pytest \
    agentic/kaggle_ai_agents/tests -q
  # Should see: "72 passed"
  ```

- [ ] **Backend ready** (choose ONE):
  - [ ] **direct_script** — Ready now, no setup needed
  - [ ] **google_adk** — Ready now, no setup needed
  - [ ] **ollama** — If choosing this:
    - [ ] Ollama installed (`brew install ollama` or https://ollama.ai)
    - [ ] Model pulled (`ollama pull llama2`)
    - [ ] Server started (`ollama serve` in background)

- [ ] **Team roles assigned** (at minimum):
  - [ ] Developer: _______________
  - [ ] QA Verifier: _______________

---

### 🎯 Execution Plan by Team Size

#### Solo Developer (1-2 hours)
1. Use **direct_script** backend (no dependencies)
2. Run `run_daily_brief_with_backend("direct_script", use_real_sources=False)`
3. Verify 10-card brief is generated
4. Check schema validation passes
5. Run full test suite to confirm

#### Small Team (2-3 people, 3-4 hours)
1. **Developer** sets up **google_adk** backend
2. **QA** prepares evaluation checklist
3. Run workflow with stub data, verify brief quality
4. Run evaluation: compare against baseline
5. Document findings, run full test suite

#### Research Team (3-4 people, 4-6 hours)
1. **DevOps** sets up **ollama** backend with llama2
2. **Developer** runs workflow with real sources
3. **LLM Researcher** manually evaluates story rankings vs keyword-based
4. **QA** validates schema and compares to baseline
5. Document LLM ranking quality differences
6. Run full test suite

---

### 🔍 Evaluation Criteria

Use these criteria to assess whether the PoC is ready:

**Must-Have (All Required)**
- [ ] All 72 tests pass
- [ ] Brief JSON passes schema validation
- [ ] Brief contains exactly 10 cards
- [ ] Each card has: rank, title, url, why_it_matters
- [ ] No broken URLs (Pydantic HttpUrl enforced)

**Should-Have (Recommended)**
- [ ] Evaluation score within 5% of baseline (if comparing to production)
- [ ] Brief generation takes <1 min (stubs) or <15 min (real sources)
- [ ] All configured sources fetch without timeout
- [ ] Cards include diverse sources (news, videos, papers, research)

**Nice-To-Have (Optional, Research)**
- [ ] LLM-based ranking produces subjectively better results than keyword-based
- [ ] Agent can switch backends without code changes
- [ ] Ollama produces rankings with clear reasoning
- [ ] Multiple LLM models produce consistent results

---

### ⚠️ Common Assessment Gaps & How to Fix

| Problem | Symptom | Resolution |
|---------|---------|-----------|
| **Missing Python 3.11** | `ModuleNotFoundError` on imports | Install Python 3.11.12 via pyenv or system package manager |
| **Missing dependencies** | `ImportError: No module named 'pydantic'` | Run `pip install -r requirements-dev.txt` |
| **Tests fail at import** | `PYTHONPATH not set` | Prepend `PYTHONPATH=src` to pytest commands |
| **Ollama backend chosen but not installed** | `RuntimeError: ollama package not installed` | Install: `pip install ollama` + `brew install ollama` + `ollama pull llama2` |
| **Sources timeout** | Tests hang for 5+ min on real sources | Use `use_real_sources=False` for initial validation |
| **URL validation fails** | `PydanticCustomError: URL scheme not allowed` | Check sources in `config/project.yaml` use only `http://` or `https://` |

---

### 📊 Assessment Summary Template

Print and complete before execution:

```
TEAM ASSESSMENT FORM
Date: _______________

PEOPLE
├─ Developer(s): ________________________  Available: _______
├─ QA Verifier: __________________________  Available: _______
├─ DevOps (if Ollama): ____________________  Available: _______
└─ Optional: ______________________________  Available: _______

INFRASTRUCTURE
├─ Python 3.11+: ☐ Yes  ☐ No
├─ Dependencies installed: ☐ Yes  ☐ No
├─ Tests passing locally: ☐ Yes  ☐ No
├─ Chosen backend: 
│  ☐ direct_script (ready now)
│  ☐ google_adk (ready now)
│  └─ ollama (needs setup)
│     ├─ Ollama installed: ☐ Yes  ☐ No
│     ├─ Model pulled: ☐ Yes  ☐ No
│     └─ Server running: ☐ Yes  ☐ No
└─ Network: ☐ Local only  ☐ Cloud access needed

EXECUTION READINESS
├─ MVP Definition agreed: ☐ Yes  ☐ No
├─ Success criteria documented: ☐ Yes  ☐ No
├─ Evaluation plan finalized: ☐ Yes  ☐ No
└─ Timeline set: ☐ Yes  ☐ No

SIGNED OFF
Developer: ________________________  Date: _______________
QA: ______________________________  Date: _______________
```

---

## Run the tests

```bash
PYTHONPATH=agentic/kaggle_ai_agents/src python -m pytest agentic/kaggle_ai_agents/tests -q
```

All 21 tests should pass. Run this after any code change.

---

## Run the evaluation (baseline parity check)

Generate a brief first, then evaluate it against the production baseline:

```bash
# 1. Produce a brief
PYTHONPATH=agentic/kaggle_ai_agents/src python -m kaggle_ai_agents.cli > /tmp/brief.json

# 2. Evaluate against app/index.json (uses latest prefix by default)
python agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py \
  /tmp/brief.json \
  app/index.json

# 3. Evaluate against a specific prefix
python agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py \
  /tmp/brief.json \
  app/index.json \
  --prefix 20260709051615
```

Exit 0 = within required threshold (≤5%). Exit 1 = fails — do not publish.

---

## Validate an artifact

Check whether a brief JSON file is schema-valid before publishing:

```bash
python agentic/kaggle_ai_agents/skills/artifact_validation/scripts/validate.py \
  /path/to/brief.json
```

---

## Deduplicate and rank items

Given a JSON file of raw items, produce a ranked shortlist:

```bash
python agentic/kaggle_ai_agents/skills/dedupe_and_rank/scripts/rank.py \
  /path/to/items.json \
  --limit 10
```

Input format: `[{source_id, title, url, summary}, ...]`

---

## Add a new source

1. Open `agentic/kaggle_ai_agents/config/project.yaml`.
2. Add an entry under `sources:` with the required fields:

```yaml
- id: my-new-source
  kind: rss          # rss | web_scrape | youtube_channel | js_crawl | structured_json
  label: My Source
  url: https://example.com/feed.xml
  limit: 10          # optional
```

3. Run `tests/test_tools.py` and add a spot-check assertion for the new source id in `test_load_source_registry_has_full_inventory`.

Source kinds:
- `rss` — standard RSS/Atom feed
- `web_scrape` — HTML page with no public API
- `youtube_channel` — YouTube channel with a `channel_id`
- `js_crawl` — JS-rendered page that needs a headless browser
- `structured_json` — public JSON API endpoint

---

## Add a new skill

1. Create a directory under `agentic/kaggle_ai_agents/skills/<skill-name>/`.
2. Add a `SKILL.md` with required frontmatter:

```
---
name: skill-name          # must match directory name, lowercase-hyphens
description: One sentence — what it does and when to use it.
metadata:
  author: kaggle-ai-agents
  version: "1.0"
---

# Skill Name

Instructions for the agent...
```

3. Optionally add:
   - `scripts/` — Python scripts the agent can run (exit 0 = pass, 1 = fail)
   - `references/` — reference docs loaded on demand
   - `assets/` — templates and examples

4. If the skill has scripts, add a test in `tests/test_skills.py`:

```python
def test_my_skill_script_passes() -> None:
    result = _run(SKILLS_DIR / "my-skill/scripts/run.py", tmp_input)
    assert result.returncode == 0, result.stderr
```

5. Run the full test suite to confirm `test_all_skills_have_skill_md` and `test_all_skill_md_have_required_frontmatter` pick up the new skill.

---

## Update the skills review table

After adding or changing a skill, update `day_3/skills_review.md` — specifically the **Skills Inventory** table — to reflect the new status and evidence path.

---

## Add a new test

Tests live in `agentic/kaggle_ai_agents/tests/`.

- Tool logic → `test_tools.py`
- Workflow → `test_workflow.py`
- Schema validation → `test_validation.py`
- Baseline evaluation → `test_baseline_eval.py`
- Skill structure and scripts → `test_skills.py`

Run with:
```bash
PYTHONPATH=agentic/kaggle_ai_agents/src python -m pytest agentic/kaggle_ai_agents/tests -q
```

---

## Commit changes

Always run tests before committing. Use a descriptive message with a substantive PII trailer:

```bash
git add -A && git commit \
  -m "Short description of the change" \
  -m "Bullet detail 1" \
  -m "Bullet detail 2" \
  -m "PII-Reviewed: <brief statement that no secrets or private data are present>"
```
