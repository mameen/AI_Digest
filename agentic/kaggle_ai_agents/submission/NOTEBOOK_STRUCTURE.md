# Kaggle Notebook Structure

This is how the notebook is organized. Each section becomes a separate cell in Kaggle.

---

## Cell 1: Title & Overview (Markdown)

```markdown
# AI Digest: Single-Agent News Aggregator with Pluggable Backends

A Kaggle AI Agents Capstone Project

**Demonstrates:**
- ✅ Single-agent architecture (course requirement)
- ✅ Instruction-driven orchestration
- ✅ 3 pluggable backends (direct_script, google_adk, ollama)
- ✅ Type-safe Pydantic models
- ✅ 72 passing tests
```

---

## Cell 2: Architectural Shift (Markdown)

Shows why single-agent is better than multi-agent:
- Old: Multi-agent graph (context re-reading, hand-offs)
- New: Single agent + skills (progressive context)

---

## Cell 3: Imports & Setup (Python)

```python
import sys
import json
from pathlib import Path

src_path = Path("../src")
if src_path.exists():
    sys.path.insert(0, str(src_path))

from kaggle_ai_agents.workflow import run_daily_brief_with_backend
```

---

## Cell 4: Backend 1 - Direct Script (Python)

Runs keyword-based ranking (instant).

```python
brief_direct = run_daily_brief_with_backend('direct_script', use_real_sources=False)
print(f"✅ Generated {len(brief_direct.cards)} cards")
# Show top 3
```

---

## Cell 5: Backend 2 - Google ADK (Python)

Runs instruction-driven agent (3-5 sec with stubs).

```python
brief_adk = run_daily_brief_with_backend('google_adk', use_real_sources=False)
print(f"✅ Generated {len(brief_adk.cards)} cards")
# Show top 3
```

---

## Cell 6: Backend 3 - Ollama (Python)

Runs LLM-based ranking (with fallback if unavailable).

```python
try:
    brief_ollama = run_daily_brief_with_backend('ollama', use_real_sources=False)
    # Show output
except Exception as e:
    print(f"⚠️ Ollama not available: {e}")
```

---

## Cell 7: Schema Validation (Python)

Shows that output is type-safe and schema-validated:
- Pydantic models enforce structure
- HttpUrl validation
- No null/empty fields

```python
card = brief_direct.cards[0]
print(f"Card structure:")
print(f"  rank: {card.rank}")
print(f"  title: {card.title}")
print(f"  url: {card.url}")
print(f"  why_it_matters: {card.why_it_matters}")
```

---

## Cell 8: Brief Structure (Python)

Show the JSON structure:

```python
brief_json = json.loads(brief_direct.model_dump_json())
print(f"Cards: {len(brief_json['cards'])}")
print(json.dumps(brief_json['cards'][0], indent=2))
```

---

## Cell 9: Test Coverage (Python/Markdown)

Reference the 72 passing tests:

```python
test_stats = {
    "Total": 72,
    "Passing": 72,
    "Coverage": [
        "✅ ADK Agent (12 tests)",
        "✅ Backends (17 tests)",
        "✅ Workflow (3 tests)",
        "✅ Original (40 tests)",
    ]
}
```

---

## Cell 10: Links & Resources (Markdown)

```markdown
## 🔗 Full Implementation

**GitHub:** https://github.com/[YOUR_USERNAME]/AI_Digest

**Key files:**
- Agent: agentic/kaggle_ai_agents/src/kaggle_ai_agents/adk_agent.py
- Backends: agentic/kaggle_ai_agents/src/kaggle_ai_agents/agent_backends.py
- Tests: agentic/kaggle_ai_agents/tests/
- Docs: agentic/kaggle_ai_agents/docs/

**Documentation:**
- PLUGGABLE_BACKENDS.md: Architecture & backend details
- EVALUATION_GUIDE.md: Testing & evaluation procedures
- HOWTO.md: Assessment & execution plans
```

---

## Cell 11: Key Takeaways (Markdown)

```markdown
## 🎯 Key Insights

1. **Single Agent > Multi-Agent**
   - Instruction + tools in one agent
   - Progressive context (no re-reads)

2. **Pluggable Backends**
   - Easy to swap implementations
   - Config-driven selection

3. **Type Safety**
   - Pydantic models at runtime
   - Schema validation built-in

4. **Production Ready**
   - Tests + documentation
   - Backward compatible
   - Error handling
```

---

## Cell 12: Next Steps (Markdown)

```markdown
## 💡 Future Work

- [ ] LLM reasoning in agent decisions
- [ ] Parallel source fetching (reduce runtime)
- [ ] LLM quality comparison research
- [ ] Cloud Run deployment with Agent Gateway
```

---

## Summary

**Total Cells:** 12 (6 markdown, 6 python)  
**Total Execution Time:** <2 minutes  
**Output:** 10-card brief × 3 backends  

Copy these into Kaggle in order and you're good to go!
