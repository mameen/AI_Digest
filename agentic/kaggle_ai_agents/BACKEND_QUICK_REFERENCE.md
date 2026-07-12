# Agent Backend Quick Reference

## 3 Ways to Use the Agent System

### 1️⃣ Config-Driven (Recommended for Production)

Edit `config/project.yaml`:
```yaml
agent:
  backend: "google_adk"  # or "direct_script", "ollama"
  backends:
    google_adk:
      instruction: "You are an AI news curator..."
```

Then use in code:
```python
from kaggle_ai_agents.workflow import run_daily_brief_with_backend

# Automatically uses backend from config
brief = run_daily_brief_with_backend()
```

### 2️⃣ Explicit Backend Selection

Override backend for this run:
```python
from kaggle_ai_agents.workflow import run_daily_brief_with_backend

# Use direct_script backend regardless of config
brief = run_daily_brief_with_backend("direct_script")

# Use ollama with stub data
brief = run_daily_brief_with_backend("ollama", use_real_sources=False)
```

### 3️⃣ Direct Backend Usage (For Advanced Use)

```python
from kaggle_ai_agents.agent_backends import get_agent_backend

# Get any backend
backend = get_agent_backend("ollama", config={
    "base_url": "http://localhost:11434",
    "model": "mistral"
})

brief = backend.forward("Generate today's digest", use_real_sources=True)
```

---

## Backend Comparison

| Aspect | direct_script | google_adk | ollama |
|--------|---|---|---|
| Speed (stubs) | 🚀 0.5s | 🔷 3-5s | 🤖 5-10s |
| Speed (real) | ⚡ 30-60s | 🔷 6-10min | 🤖 6-15min |
| Deterministic | ✅ Yes | ✅ Yes | ❌ No (LLM) |
| Course Aligned | ❌ No | ✅ Yes | ⚠️ Experimental |
| LLM Integration | ❌ None | ✨ Ready | ✅ Active |
| Dependencies | Python stdlib | Python stdlib | `ollama` package |
| Setup | None | None | Install + Run Ollama |
| Production Ready | ⚠️ Testing only | ✅ Yes | ⚠️ Needs fallback |

---

## Setup Guides

### Direct Script (No Setup Needed)
```bash
# Ready to use immediately
python -c "from kaggle_ai_agents.workflow import run_daily_brief_with_backend; print(run_daily_brief_with_backend('direct_script'))"
```

### Google ADK (Already Configured)
```bash
# Uses default instruction, no extra setup
python -c "from kaggle_ai_agents.workflow import run_daily_brief_with_backend; print(run_daily_brief_with_backend('google_adk'))"
```

### Ollama (3 Steps)
```bash
# 1. Install Ollama
brew install ollama  # or https://ollama.ai

# 2. Start Ollama (in background)
ollama serve &

# 3. Pull a model
ollama pull llama2   # ~4GB, or try "mistral" (~5GB)

# 4. Update config
# Modify config/project.yaml to set backend: "ollama"

# 5. Use it
python -c "from kaggle_ai_agents.workflow import run_daily_brief_with_backend; print(run_daily_brief_with_backend())"
```

---

## Configuration Examples

### Minimal (Direct Script)
```yaml
agent:
  backend: "direct_script"
```

### Standard (Google ADK with Custom Instruction)
```yaml
agent:
  backend: "google_adk"
  backends:
    google_adk:
      instruction: |
        You are an AI researcher assistant. Find the most important AI/ML papers
        and research from today's sources. Focus on novel architectures, benchmarks,
        and breakthrough results. Explain each story's significance.
```

### Advanced (Ollama with LLM Parameters)
```yaml
agent:
  backend: "ollama"
  backends:
    ollama:
      base_url: "http://localhost:11434"
      model: "mistral"        # Faster than llama2
      temperature: 0.5        # More deterministic
      top_p: 0.8              # Narrow sampling
```

### Multi-Backend Setup
```yaml
agent:
  backend: "google_adk"       # Default
  backends:
    direct_script:
      description: "For CI/CD testing"
    google_adk:
      instruction: "Your instruction here"
    ollama:
      base_url: "http://localhost:11434"
      model: "neural-chat"
      temperature: 0.7
```

---

## Common Use Cases

### 1. **Fast Testing**
```python
brief = run_daily_brief_with_backend("direct_script", use_real_sources=False)
# ✅ Takes ~0.5s, perfect for CI/CD
```

### 2. **Production with Real Sources**
```python
# Set backend: "google_adk" in config
brief = run_daily_brief_with_backend()
# ✅ Takes 6-10min, fully deterministic, course-aligned
```

### 3. **Research with LLM Ranking**
```python
# Set backend: "ollama" in config, install ollama, run: ollama serve
brief = run_daily_brief_with_backend()
# ✅ Takes 6-15min, uses LLM for smarter ranking (experimental)
```

### 4. **Compare All Backends**
```python
from kaggle_ai_agents.workflow import run_daily_brief_with_backend

for backend_name in ["direct_script", "google_adk", "ollama"]:
    try:
        brief = run_daily_brief_with_backend(backend_name, use_real_sources=False)
        print(f"{backend_name}: {len(brief.cards)} cards")
    except Exception as e:
        print(f"{backend_name}: Failed - {e}")
```

---

## Troubleshooting

**"Could not auto-detect project.yaml"**
- Ensure you're in the repo root or have proper PYTHONPATH set
- Explicitly pass path: `load_agent_config("/path/to/project.yaml")`

**Ollama "Connection refused"**
- Check if Ollama is running: `ps aux | grep ollama`
- Start it: `ollama serve`
- Verify url is correct in config

**Ollama "Model not found"**
- Pull the model: `ollama pull llama2`
- Available models: llama2, mistral, neural-chat, etc.

**Slow discovery**
- YouTube discovery is slowest (~5min). It's normal with real sources.
- Use `use_real_sources=False` for testing.
- Reduce sources in `config/project.yaml` to speed up.

---

## Testing

### Run Backend Tests Only
```bash
PYTHONPATH=src python -m pytest tests/test_agent_backends.py -v
```

### Run Full Suite
```bash
PYTHONPATH=src python -m pytest tests -q
# ~12-15min (includes real source discovery)
```

### Test Specific Backend
```bash
PYTHONPATH=src python -m pytest tests/test_agent_backends.py::TestOllamaBackend -v
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `agent_backends.py` | Backend implementations + factory |
| `workflow.py` | Entry points (backward compatible) |
| `adk_agent.py` | ADK-style orchestrator |
| `config/project.yaml` | Configuration (agent section) |
| `tests/test_agent_backends.py` | 17 tests for all backends |
| `docs/PLUGGABLE_BACKENDS.md` | Full documentation |
| `examples/agent_backends_example.py` | Usage examples |

---

## Architecture

```
run_daily_brief_with_backend()
    ↓
load_agent_config()  ← reads config/project.yaml
    ↓
get_agent_backend()  ← factory pattern
    ↓
    ├─ DirectScriptBackend.forward()
    ├─ GoogleADKBackend.forward() → ADKAgent
    └─ OllamaBackend.forward() → Ollama LLM
    ↓
DailyBrief (10 cards)
```

---

## Next Steps

1. **Try each backend** with stubs: `run_daily_brief_with_backend("backend", use_real_sources=False)`
2. **Pick one for production** - edit `config/project.yaml` to set default
3. **Test with real sources** if time permits
4. **For LLM experimmentation** - install Ollama and try the ollama backend

All backends produce the same `DailyBrief` output, so switching is seamless! 🎯
