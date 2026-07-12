# How to Submit to Kaggle

## Step-by-Step Submission Guide

### 1. **Go to Competition Page**
Navigate to: https://www.kaggle.com/competitions/vibecoding-agents-capstone-project/code

### 2. **Create New Notebook**
- Click blue **"Create"** button or **"New Notebook"**
- Choose **Python** language
- Title it: `"AI Digest: Single-Agent News Aggregator with Pluggable Backends"`

### 3. **Copy Notebook Content**
- Open `kaggle_notebook_submission.md` in this folder
- Copy each cell (markdown and code sections) into your Kaggle notebook
- Each `---` separator indicates a new cell

### 4. **Add Inputs (Optional)**
If Kaggle requires inputs:
- You can link to your GitHub repo as input
- Or leave blank (notebook is self-contained with stubs)

### 5. **Test Run**
- Click **"Run All"** or **"Commit and Run"**
- Should complete in **30-60 seconds** (using stubs)
- Check output shows 10 cards generated

### 6. **Submit**
- Click **"Commit"** button (top right)
- Kaggle will auto-save and show version number
- **✅ You're submitted!**

---

## What Judges See

When judges view your notebook, they'll see:

1. **Architecture explanation** — Why single-agent + skills is better
2. **Live demo** — All 3 backends showing output (instant, with stubs)
3. **Code quality** — Clean Python, type hints, tests reference
4. **GitHub link** — For full code, docs, test suite
5. **Next steps** — How to run with real sources

---

## Key Points for Judges

**Course Alignment:**
- ✅ **Single agent** with instruction-driven orchestration (not multi-agent)
- ✅ **Tools/Skills** as subprocess-based functions
- ✅ **Pluggable backends** showing flexibility (Google ADK, direct script, Ollama)

**Implementation Quality:**
- ✅ **72 tests passing** (reference in notebook)
- ✅ **Type-safe Pydantic models** (NewsItem, DailyBrief)
- ✅ **Schema validation** (10 cards with rank/title/url/why_it_matters)
- ✅ **Real sources** working (reference in GitHub README)

**Production Readiness:**
- ✅ **Backward compatible** (old functions still work)
- ✅ **Config-driven** (easy to swap backends)
- ✅ **Error handling** (graceful fallbacks)
- ✅ **Documentation** (HOWTO.md, EVALUATION_GUIDE.md, README.md)

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Notebook won't run | Make sure all imports work; test on local machine first |
| Takes too long | Using `use_real_sources=True` takes 6-10min; submit with stubs (False) for speed |
| Can't find module | Check PYTHONPATH in first cell if cloning from GitHub |
| Output not showing | Add `print()` or `display()` statements in notebook cells |

---

## Tips for Best Impression

1. **Keep it focused** — Show the key idea (single agent, 3 backends) in <2 min
2. **Make it run fast** — Use stubs so judges see it complete
3. **Link to depth** — GitHub has full code, tests, documentation
4. **Show schema** — Display one card with all fields (proves validation)
5. **Explain the choice** — Why you chose single-agent over multi-agent (course insight)

---

## File Contents

- **`kaggle_notebook_submission.md`** — Complete notebook content (copy into Kaggle)
- **`how_to_submit.md`** — This file (submission instructions)
- **`kaggle_submission_summary.txt`** — Quick reference for copy/paste

---

## GitHub Reference

Judges will also see your full project at:
```
https://github.com/[your-username]/AI_Digest
agentic/kaggle_ai_agents/
├── src/
│   ├── kaggle_ai_agents/
│   │   ├── adk_agent.py (single-agent orchestrator)
│   │   ├── agent_backends.py (3 pluggable backends)
│   │   └── workflow.py (config-driven entry point)
├── tests/ (72 tests, all passing)
├── docs/ (PLUGGABLE_BACKENDS.md, EVALUATION_GUIDE.md)
├── README.md (architecture & quick start)
└── HOWTO.md (assessment & detailed guide)
```

---

**Good luck with your submission!** 🚀
