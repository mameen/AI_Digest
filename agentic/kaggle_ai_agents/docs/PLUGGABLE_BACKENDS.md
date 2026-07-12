# Pluggable Agent Backends

This document describes the configurable agent backend system for the AI Digest daily brief workflow.

## Overview

The workflow now supports multiple agent execution strategies through a pluggable backend system:

| Backend | Speed | Best For | Requirements |
|---------|-------|----------|--------------|
| **direct_script** | ⚡ Fast (~30-60s) | Testing, CI/CD, deterministic | None (Python stdlib) |
| **google_adk** | 🔷 Medium (6-10min with real sources) | Course requirements, instruction-driven | Existing setup |
| **ollama** | 🤖 Depends on LLM (experimental) | Research, LLM-based ranking, privacy | Ollama installed + running |

## Configuration

Backend selection is driven by `config/project.yaml`:

```yaml
agent:
  # Active backend: "direct_script", "google_adk", or "ollama"
  backend: "google_adk"
  
  backends:
    direct_script:
      description: "Hardcoded orchestration (deterministic, fast for tests)"
    
    google_adk:
      description: "ADK agent with tools (instruction-based, course-aligned)"
      instruction: |
        You are an AI news curator. Your job is to find the latest and most important 
        AI/ML stories from configured sources...
    
    ollama:
      description: "Local Ollama LLM agent (experimental, requires Ollama installed)"
      base_url: "http://localhost:11434"
      model: "llama2"  # or "mistral", "neural-chat", etc.
      temperature: 0.7
      top_p: 0.9
```

## Usage

### Option 1: Config-Driven (Recommended for Production)

```python
from kaggle_ai_agents.workflow import run_daily_brief_with_backend

# Uses backend from project.yaml
brief = run_daily_brief_with_backend()

# With stub data for testing
brief = run_daily_brief_with_backend(use_real_sources=False)
```

### Option 2: Explicit Backend Selection

```python
# Override config for this run
brief = run_daily_brief_with_backend("direct_script")

# Different backend, stub data
brief = run_daily_brief_with_backend("google_adk", use_real_sources=False)
```

### Option 3: Legacy Entry Points (Backward Compatible)

```python
from kaggle_ai_agents.workflow import (
    run_daily_brief,                 # Direct script (fast, stubs by default)
    run_daily_brief_with_agent,      # Google ADK (instruction-based)
)

# These still work exactly as before
brief = run_daily_brief(use_real_sources=False)
brief = run_daily_brief_with_agent(use_real_sources=False)
```

## Backend Details

### 1. Direct Script Backend

**What it does:**
- Calls discovery, ranking, and validation functions directly
- Deterministic orchestration (no LLM reasoning)
- No external dependencies

**When to use:**
- Fast unit tests
- CI/CD pipelines
- Baseline comparison

**Example:**
```python
from kaggle_ai_agents.agent_backends import DirectScriptBackend

backend = DirectScriptBackend("direct_script")
brief = backend.forward("Generate today's digest", use_real_sources=False)
```

### 2. Google ADK Backend

**What it does:**
- Implements ADK-style single agent + tools pattern
- Uses instruction-driven orchestration
- Extensible for future LLM integration

**When to use:**
- Course requirements alignment
- Production workflows where you want instruction-based orchestration
- Future LLM integration (just add reasoning logic to agent.forward())

**Example:**
```python
from kaggle_ai_agents.agent_backends import GoogleADKBackend

config = {
    "instruction": "You are an AI news curator. Find the latest AI/ML stories..."
}
backend = GoogleADKBackend("google_adk", config)
brief = backend.forward("Generate today's digest", use_real_sources=True)
```

### 3. Ollama Backend (Experimental)

**What it does:**
- Calls local Ollama LLM for story ranking
- Uses discovery and validation scripts (only replaces ranking)
- Gracefully falls back to script-based ranking if Ollama unavailable

**When to use:**
- Research and experimentation
- Privacy-conscious environments (LLM runs locally)
- Fine-tuning LLM-based ranking strategies

**Setup:**
```bash
# 1. Install Ollama
brew install ollama  # macOS
# or visit https://ollama.ai for other OSes

# 2. Start Ollama server
ollama serve

# 3. Pull a model (in another terminal)
ollama pull llama2  # ~4GB
# or: ollama pull mistral  # ~5GB
# or: ollama pull neural-chat  # ~5GB

# 4. Update config/project.yaml
# agent:
#   backend: "ollama"
#   backends:
#     ollama:
#       base_url: "http://localhost:11434"
#       model: "llama2"
```

**Example:**
```python
from kaggle_ai_agents.agent_backends import OllamaBackend

config = {
    "base_url": "http://localhost:11434",
    "model": "llama2",
    "temperature": 0.7,
}
backend = OllamaBackend("ollama", config)
brief = backend.forward("Generate today's digest", use_real_sources=False)
```

## Architecture

### Backend Interface

All backends implement `AgentBackend` abstract base class:

```python
class AgentBackend(ABC):
    def __init__(self, name: str, config: dict[str, Any] | None = None):
        self.name = name
        self.config = config or {}
    
    @abstractmethod
    def forward(self, prompt: str, use_real_sources: bool = True) -> DailyBrief:
        """Execute agent forward pass and return brief."""
        pass
```

### Factory Pattern

Get backends via factory function:

```python
from kaggle_ai_agents.agent_backends import get_agent_backend

backend = get_agent_backend("google_adk", config={"instruction": "..."})
brief = backend.forward("Generate digest")
```

### Config Auto-Detection

Automatic path resolution to find `config/project.yaml`:

```python
from kaggle_ai_agents.agent_backends import load_agent_config

backend_name, backend_config = load_agent_config()
# Returns: ("google_adk", {"instruction": "...", ...})
```

## Adding a New Backend

1. Create a new class that extends `AgentBackend`:

```python
class MyCustomBackend(AgentBackend):
    def forward(self, prompt: str, use_real_sources: bool = True) -> DailyBrief:
        # Your orchestration logic here
        pass
```

2. Register it in the factory:

```python
def get_agent_backend(backend_name: str, config: dict[str, Any] | None = None) -> AgentBackend:
    backends = {
        "direct_script": DirectScriptBackend,
        "google_adk": GoogleADKBackend,
        "ollama": OllamaBackend,
        "my_custom": MyCustomBackend,  # Add here
    }
    # ...
```

3. Add configuration to `config/project.yaml`:

```yaml
agent:
  backends:
    my_custom:
      description: "My custom backend"
      # Add backend-specific config here
```

## Testing

All backends are tested in `tests/test_agent_backends.py`:

```bash
PYTHONPATH=src python -m pytest tests/test_agent_backends.py -v
```

Test coverage:
- ✅ Backend instantiation
- ✅ Forward pass with stub data
- ✅ Factory pattern
- ✅ Config loading and auto-detection
- ✅ Integration with workflow module
- ✅ Graceful fallbacks (Ollama → script-based)

## Performance Characteristics

### With Stub Data (fast)
- direct_script: ~0.5s
- google_adk: ~3-5s (tool initialization overhead)
- ollama: ~5-10s (LLM inference)

### With Real Sources
- direct_script: ~30-60s (YouTube discovery is slowest)
- google_adk: ~6-10min (same discovery, LLM tool overhead)
- ollama: ~6-15min (discovery + LLM ranking)

### Breakdown (Real Sources)
- Discovery: ~5-6min (YouTube channels, arXiv, RSS)
- Ranking: ~30-60s (script-based), ~1-5min (LLM-based)
- Validation: <1s
- **Total: ~6-15min depending on backend**

## Troubleshooting

### "Could not auto-detect project.yaml"
Provide explicit path:
```python
from kaggle_ai_agents.agent_backends import load_agent_config

backend_name, config = load_agent_config(
    config_path="/path/to/agentic/kaggle_ai_agents/config/project.yaml"
)
```

### Ollama "Connection refused"
1. Verify Ollama is running: `ollama serve`
2. Check base_url in config (default: `http://localhost:11434`)
3. Restart Ollama: kill the process and run `ollama serve` again

### Ollama "Model not found"
Pull the model:
```bash
ollama pull llama2
```

### Timeout errors
Increase discovery timeout or reduce sources in `config/project.yaml`.

## Future Enhancements

Potential backends to add:
- **Claude** - Anthropic's Claude API (paid, cloud)
- **Gemini** - Google's Gemini API (paid, cloud)
- **Local GPU** - vLLM, TensorRT-LLM for faster local LLM
- **LM Studio** - Alternative local LLM server
- **Chain-of-Thought** - Multi-step LLM reasoning for ranking

## References

- `agent_backends.py` - Backend implementations
- `workflow.py` - Integration with workflow
- `adk_agent.py` - Google ADK-style agent
- `config/project.yaml` - Configuration
- `tests/test_agent_backends.py` - Test suite
