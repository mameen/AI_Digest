# PoC Evaluation Guide

**How to properly assess, run, and evaluate this AI Agents proof-of-concept.**

---

## 1. Pre-Execution Assessment

Before you start, complete the checklist below. This ensures your team and infrastructure are ready.

### Team Role Assessment

| Role | Assessment Question | Pass? | Action if No |
|------|---------------------|-------|-------------|
| **Developer** | Can you run `pytest` and read the output? | ☐ | Take 30min Python/pytest intro |
| | Can you read Python tracebacks? | ☐ | Familiar with Python error messages |
| | Can you use git to revert changes? | ☐ | Practice git reset, checkout |
| **QA Verifier** | Can you read JSON files? | ☐ | Learn JSON structure (5 min) |
| | Can you validate against schema? | ☐ | Understand Pydantic validation errors |
| | Can you compare output files? | ☐ | Use `diff` or text comparison tool |
| **DevOps (if Ollama)** | Can you install Ollama? | ☐ | `brew install ollama` or from https://ollama.ai |
| | Can you pull a model? | ☐ | `ollama pull llama2` (~5 min download) |
| | Can you run Ollama in background? | ☐ | `ollama serve &` and verify port 11434 |
| **LLM Researcher (optional)** | Can you articulate what makes a good ranking? | ☐ | Define ranking criteria beforehand |
| | Can you run manual side-by-side comparison? | ☐ | Have a comparison template ready |

### Infrastructure Assessment

| Component | Check | Pass? | Fix |
|-----------|-------|-------|-----|
| **Python 3.11+** | `python3 --version` | ☐ | Install via pyenv or system package |
| **pip packages** | `pip list \| grep pydantic` | ☐ | `pip install -r requirements-dev.txt` |
| **Tests** | `PYTHONPATH=src pytest ... -q` | ☐ | Run `pytest agentic/kaggle_ai_agents/tests` |
| **Backend (if Ollama)** | `ollama list` shows a model | ☐ | `ollama pull llama2` |
| **Ollama server** | `curl localhost:11434` returns 200 | ☐ | `ollama serve &` |

### Success Criteria Agreement

Before execution, the team should agree:

- [ ] **What is "passing"?** (All tests passing? 10 cards generated? Schema valid? Evaluation within 5%?)
- [ ] **What is "good ranking"?** (Diverse sources? Breaking news first? Relevance score?)
- [ ] **What is "failure"?** (Critical: tests fail? Timeouts? Nice-to-have: LLM ranking below baseline?)
- [ ] **Time budget:** How long can we run this? (Stubs: 1 min, Real sources: 15 min)

---

## 2. Execution Plan by Backend

### Scenario A: Direct Script (No LLM, ~20 minutes total)

**Use this to validate the PoC works at all.**

```bash
# Step 1: Run with stubs (instant)
PYTHONPATH=src python -c "
  from kaggle_ai_agents.workflow import run_daily_brief_with_backend
  brief = run_daily_brief_with_backend('direct_script', use_real_sources=False)
  print(f'Cards: {len(brief.cards)}')
  assert len(brief.cards) == 10, 'Should have 10 cards'
  print('✅ Stub test passed')
"

# Step 2: Run full test suite (5 min)
PYTHONPATH=src pytest agentic/kaggle_ai_agents/tests -q
# Expected: 72 passed

# Step 3: Validate schema
python agentic/kaggle_ai_agents/skills/artifact_validation/scripts/validate.py \
  <brief_file.json>
# Expected: exit code 0 (valid)

# Step 4: QA spot-check
cat brief.json | python -m json.tool | head -30
# Check: 10 cards, each with rank/title/url/why_it_matters, no nulls
```

**Success criteria:**
- ✅ 72 tests pass
- ✅ 10 cards generated
- ✅ JSON schema valid
- ✅ No null/empty fields

**Time:** ~20 min

---

### Scenario B: Google ADK (Course-Aligned, ~2.5 hours)

**Use this for production-like execution with real sources.**

```bash
# Step 1: Verify configuration
cat agentic/kaggle_ai_agents/config/project.yaml | grep "backend:"
# Should show: backend: "google_adk"

# Step 2: Run with stubs first (quick validation)
PYTHONPATH=src python -c "
  from kaggle_ai_agents.workflow import run_daily_brief_with_backend
  brief = run_daily_brief_with_backend('google_adk', use_real_sources=False)
  print(f'✅ Stub test: {len(brief.cards)} cards generated')
"
# Expected: ~3-5 seconds, 10 cards

# Step 3: Run with real sources (~6-10 min)
# NOTE: This fetches from YouTube, arXiv, RSS, etc.
PYTHONPATH=src python -c "
  from kaggle_ai_agents.workflow import run_daily_brief_with_backend
  brief = run_daily_brief_with_backend('google_adk', use_real_sources=True)
  with open('/tmp/brief.json', 'w') as f:
    import json
    f.write(brief.model_dump_json())
  print(f'✅ Generated {len(brief.cards)} cards from real sources')
"

# Step 4: Validate against baseline (if available)
python agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py \
  /tmp/brief.json \
  app/index.json
# Expected: Evaluation score (gap), exit code 0 if <5%

# Step 5: Full test suite
PYTHONPATH=src pytest agentic/kaggle_ai_agents/tests -q
# Expected: 72 passed
```

**Success criteria:**
- ✅ 72 tests pass
- ✅ 10 cards generated from real sources
- ✅ Evaluation within threshold (if baseline available)
- ✅ Diverse sources (news, videos, papers, research)
- ✅ Stories are recent and relevant

**Time:** ~45 min (stubs) + ~10 min (real) + ~5 min (validation)

---

### Scenario C: Ollama (LLM-Based Ranking, ~3-4 hours)

**Use this to research LLM-based ranking quality vs keyword-based.**

```bash
# Step 1: Check Ollama is running
ollama list
# Expected: see llama2 or another model listed
# If not: run `ollama serve &` in another terminal, then `ollama pull llama2`

# Step 2: Verify config points to ollama
cat agentic/kaggle_ai_agents/config/project.yaml | grep -A 5 "backend:"
# Should show backend: "ollama" with connection details

# Step 3: Run with stubs (quick test)
PYTHONPATH=src python -c "
  from kaggle_ai_agents.workflow import run_daily_brief_with_backend
  brief = run_daily_brief_with_backend('ollama', use_real_sources=False)
  print(f'✅ Ollama stubs: {len(brief.cards)} cards')
"
# Expected: ~5-10 seconds (LLM inference time)

# Step 4: Run with real sources
PYTHONPATH=src python -c "
  from kaggle_ai_agents.workflow import run_daily_brief_with_backend
  brief = run_daily_brief_with_backend('ollama', use_real_sources=True)
  with open('/tmp/brief_ollama.json', 'w') as f:
    import json
    f.write(brief.model_dump_json())
  print(f'✅ Ollama real sources: {len(brief.cards)} cards')
"
# Expected: ~10-15 min total (discovery + LLM ranking)

# Step 5: Compare Ollama vs Keyword-Based
# Generate keyword-based brief for comparison
PYTHONPATH=src python -c "
  from kaggle_ai_agents.workflow import run_daily_brief_with_backend
  brief_kw = run_daily_brief_with_backend('direct_script', use_real_sources=True)
  with open('/tmp/brief_keyword.json', 'w') as f:
    import json
    f.write(brief_kw.model_dump_json())
  print('✅ Keyword brief saved')
"

# Step 6: Manual comparison (side-by-side)
cat /tmp/brief_ollama.json | python -m json.tool | head -40
cat /tmp/brief_keyword.json | python -m json.tool | head -40
# Compare: Which ranking seems more relevant? More diverse? Better explained?

# Step 7: Full test suite
PYTHONPATH=src pytest agentic/kaggle_ai_agents/tests -q
# Expected: 72 passed
```

**LLM Evaluation Criteria:**
- ✅ LLM ranking produces 10 unique cards (no duplicates)
- ✅ Top cards include breaking news/high-impact stories
- ✅ Explanations (why_it_matters) are clear and articulate
- ✅ Diverse sources (not biased to one type)
- ⭕ **Optional:** Subjective assessment: Is this better than keyword ranking?

**Time:** ~15 min (stubs) + ~10 min (real sources) + ~10 min (keyword comparison) + ~10 min (analysis)

---

## 3. Evaluation Checklists

### Functional Testing Checklist (All Backends)

```
FUNCTIONAL TESTING CHECKLIST
Backend: _______________    Date: _______________
Tester: _________________    Time to complete: _______

TESTS PASSING
[ ] All 72 tests pass (run: pytest agentic/kaggle_ai_agents/tests -q)
    Exit code: ______ (should be 0)
    Failed tests (if any): _________________________________

BRIEF GENERATION (STUBS)
[ ] Brief generates in <10 seconds
[ ] Brief has exactly 10 cards
[ ] Each card has all required fields:
    [ ] rank (1-10)
    [ ] title (non-empty string)
    [ ] url (valid http/https URL)
    [ ] why_it_matters (non-empty string)

SCHEMA VALIDATION
[ ] Pydantic schema validation passes
[ ] No null/empty fields
[ ] URLs are valid (http/https only, no javascript: or file:)

REAL SOURCE EXECUTION (If time permits)
[ ] Real source discovery completes without timeout
[ ] Sources fetched: RSS (___), YouTube (___), arXiv (___), Other (___)
[ ] Total items discovered: _______
[ ] Top 10 ranked items are diverse (different sources)
[ ] Execution time: _______ seconds

NOTES
____________________________________________________________________________
____________________________________________________________________________
```

### Baseline Comparison Checklist (Google ADK / Ollama)

```
BASELINE COMPARISON CHECKLIST
Backend: _______________    Date: _______________
Baseline: ________________   Tester: _____________

EVALUATION METRICS
[ ] Evaluation script runs successfully
[ ] Evaluation gap: ______% (should be ≤ 5%)
[ ] Cards overlap with baseline: ______%
[ ] New cards (not in baseline): ______%

CONTENT QUALITY (Manual Review)
[ ] Top 3 cards are relevant and current
[ ] No obvious duplicates or near-duplicates
[ ] Stories span different AI/ML areas (LLMs, CV, robotics, etc.)

EXPLANATION QUALITY
[ ] why_it_matters explanations are clear (read by non-expert)
[ ] Explanations explain *why* this matters, not just what
[ ] No generic filler text

DIVERSITY CHECK
[ ] Source diversity: _____ different sources among 10 cards
    Breakdown: News (__), Videos (__), Papers (__), Research (__)
[ ] Date diversity: Oldest: _____, Newest: _____
    (Should be within last 7 days)

ISSUES FOUND (If any)
____________________________________________________________________________
____________________________________________________________________________

ASSESSMENT
Pass: ☐ Yes  ☐ No
Reason: _________________________________________________________________
```

### LLM Quality Comparison (Ollama Backend Only)

```
LLM vs KEYWORD RANKING COMPARISON
Date: _______________    LLM Researcher: ______________

SETUP
[ ] Ollama brief ready: /tmp/brief_ollama.json
[ ] Keyword brief ready: /tmp/brief_keyword.json
[ ] Both generated with same sources (real or stubs)

RANKING COMPARISON
Criteria: Is LLM ranking better than keyword ranking?

Top 5 Cards Analysis:
Ollama Top 5                  | Keyword Top 5
1. ________________________   | 1. _______________________
2. ________________________   | 2. _______________________
3. ________________________   | 3. _______________________
4. ________________________   | 4. _______________________
5. ________________________   | 5. _______________________

Verdict (circle one):
LLM Better  /  Keyword Better  /  About the Same

Reasoning: ________________________________________________________________

EXPLANATION QUALITY
Ollama explanations:
- More specific? ☐ Yes ☐ No ☐ Same
- More actionable? ☐ Yes ☐ No ☐ Same
- Better business/user context? ☐ Yes ☐ No ☐ Same

DIVERSITY
Ollama diversity score: _____ / 10
Keyword diversity score: _____ / 10
(Lower = more diverse; 10 = all same source, 1 = all different)

OVERALL ASSESSMENT
LLM ranking improves results? ☐ Yes ☐ No ☐ Needs more tuning

Recommended next steps:
_________________________________________________________________________
_________________________________________________________________________
```

---

## 4. Common Issues & Resolutions

| Issue | Symptom | Resolution |
|-------|---------|-----------|
| **Python 3.11 not found** | `python3: command not found` | Install via pyenv: `pyenv install 3.11.12 && pyenv global 3.11.12` |
| **PYTHONPATH not set** | `ModuleNotFoundError: No module named 'kaggle_ai_agents'` | Prepend to command: `PYTHONPATH=agentic/kaggle_ai_agents/src pytest ...` |
| **Tests timeout (>10min)** | Tests hang when running real sources | Use `use_real_sources=False` for validation, real sources only in final run |
| **Ollama connection refused** | `ConnectionRefusedError` on ollama backend | Start Ollama: `ollama serve &` in another terminal |
| **Ollama model not found** | `ModelNotFound: llama2 not available` | Pull model: `ollama pull llama2` (~5 min, ~4GB) |
| **URL validation fails** | `PydanticCustomError: URL scheme not allowed` | Check sources in `config/project.yaml` — only `http://` and `https://` allowed |
| **JSON parse error on brief** | `json.JSONDecodeError` when validating | Check brief is complete JSON (not truncated); validate with `python -m json.tool` |
| **Evaluation script fails** | No baseline `app/index.json` found | Evaluation optional; if missing, skip or use stub baseline |

---

## 5. Success Metrics Summary

### MVP: Minimal (Pass/Fail)
- ✅ **72 tests pass**
- ✅ **10-card brief generates**
- ✅ **Schema valid**
- ✅ **No crashes**

### Standard: Production-Ready
- ✅ MVP criteria above
- ✅ **Real sources execute** (<15 min)
- ✅ **Evaluation within threshold** (if baseline exists)
- ✅ **Diverse sources** (news, videos, papers)
- ✅ **Consistent results** (same seed → same top 10)

### Advanced: Research (Optional)
- ✅ Standard criteria above
- ✅ **LLM ranking vs keyword-based** compared
- ✅ **Ranking quality** assessed manually
- ✅ **Multiple models** tested (llama2, mistral, neural-chat)
- ✅ **Quality gains documented** (% improvement)

---

## 6. Handoff Template

When handing off to another team or wrapping up:

```
EVALUATION HANDOFF DOCUMENT
Date: _______________    From: _______________    To: _______________

EXECUTION SUMMARY
Backend used: __________    Total runtime: ___________
Tests passed: 72/72 ☐      Schema valid: ☐           Real sources: ☐

KEY FINDINGS
1. _________________________________________________________________
2. _________________________________________________________________
3. _________________________________________________________________

WHAT WORKS WELL
- _________________________________________________________________
- _________________________________________________________________

WHAT NEEDS IMPROVEMENT
- _________________________________________________________________
- _________________________________________________________________

RECOMMENDATIONS FOR NEXT PHASE
- _________________________________________________________________
- _________________________________________________________________

FILES GENERATED
Brief: ________________________    Test results: ________________
Evaluation: ___________________    Baseline: _____________________

KNOWN ISSUES
1. _________________________________________________________________
2. _________________________________________________________________

TEAM ASSESSMENT
Developers available: ________________   
Next run owner: _______________________
Time estimate (next run): _______________
```

---

## 7. Quick Reference Commands

```bash
# SETUP
pip install -r agentic/kaggle_ai_agents/requirements-dev.txt
export PYTHONPATH=agentic/kaggle_ai_agents/src

# RUN TESTS
pytest agentic/kaggle_ai_agents/tests -q              # All tests
pytest tests/test_agent_backends.py -v                # Just backend tests

# GENERATE BRIEF
python -c "
  from kaggle_ai_agents.workflow import run_daily_brief_with_backend
  brief = run_daily_brief_with_backend('direct_script', use_real_sources=False)
"

# VALIDATE SCHEMA
python agentic/kaggle_ai_agents/skills/artifact_validation/scripts/validate.py brief.json

# EVALUATE AGAINST BASELINE
python agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py brief.json app/index.json

# OLLAMA SETUP
brew install ollama
ollama serve &                          # Start server
ollama pull llama2                      # Download model
curl localhost:11434                   # Verify running

# COMMON FIXES
PYTHONPATH=src pytest ...               # Fix import errors
python3 --version                       # Check Python 3.11
pip list | grep pydantic                # Check dependencies
```

---

**For the latest updates, see: [`HOWTO.md`](HOWTO.md)**
