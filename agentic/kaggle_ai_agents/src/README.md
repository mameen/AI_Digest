# AI Digest Kaggle Agent — 3 Implementations

Refactored into 3 separate, production-grade backends:

1. **`fully_scripted/`** — No LLM, keyword-based ranking
2. **`google_adk/`** — Google Gemini API ranking
3. **`ollama_agent/`** — Local Ollama + LangChain ReAct

---

## Quick Start

### 1. Fully Scripted (No dependencies beyond stdlib)

```bash
cd agentic/kaggle_ai_agents
python -m src.fully_scripted.runner
```

**Output:** `brief_output.json`  
**Time:** ~10 seconds (network I/O only)

---

### 2. Google ADK (Requires Gemini API key)

```bash
export GEMINI_API_KEY="your-api-key"
python -m src.google_adk.runner
```

**Output:** `brief_output_adk.json`  
**Time:** ~30 seconds (API calls)

---

### 3. Ollama Agent (Requires LangChain + Ollama)

**Setup:**
```bash
# Install LangChain deps
pip install langchain langchain-ollama langchain-core

# Start Ollama
ollama serve

# Download model (if needed)
ollama pull qwen2.5-coder:14b
```

**Run:**
```bash
python -m src.ollama_agent.runner
```

**Output:** `brief_output_ollama.json`  
**Time:** ~60 seconds (LLM generation)

---

## Architecture

```
src/
├── base/                    # Shared abstractions
│   ├── agent.py            # Abstract Agent base class
│   ├── models.py           # NewsItem, BriefCard, DailyBrief
│   ├── skills.py           # Skill interface
│   └── config.py           # Config loading
│
├── fully_scripted/          # Direct calls, keyword ranking
│   ├── agent.py            # FullyScriptedAgent
│   └── runner.py           # Entry point
│
├── google_adk/             # ADK + Gemini
│   ├── agent.py            # GoogleADKAgent
│   └── runner.py           # Entry point
│
└── ollama_agent/           # LangChain + ReAct
    ├── agent.py            # OllamaAgent
    ├── tools.py            # @tool decorated functions
    └── runner.py           # Entry point
```

---

## Data Flow

All 3 implementations follow the same pipeline:

```
discover()  → [NewsItem, ...]
     ↓
rank()      → [ranked NewsItem, ...]
     ↓
validate()  → DailyBrief(10 cards)
```

**Difference:** How each backend ranks:
- **fully_scripted:** Keyword scoring (no network)
- **google_adk:** Gemini API (network, requires key)
- **ollama_agent:** Local LLM via LangChain (no external APIs)

---

## Testing

**Test all 3 backends:**
```bash
python -m src.fully_scripted.runner && echo "✅ fully_scripted passed"
python -m src.google_adk.runner && echo "✅ google_adk passed"
python -m src.ollama_agent.runner && echo "✅ ollama_agent passed"
```

**Compare outputs:**
```bash
diff brief_output.json brief_output_adk.json
diff brief_output_adk.json brief_output_ollama.json
```

---

## Key Classes

### `Agent` (base class)

```python
class Agent(ABC):
    @abstractmethod
    def discover(self) -> List[NewsItem]: ...
    
    @abstractmethod
    def rank(self, items: List[NewsItem], count: int = 10) -> List[NewsItem]: ...
    
    @abstractmethod
    def validate(self, items: List[NewsItem]) -> DailyBrief: ...
    
    def run(self) -> DailyBrief:
        # Orchestrates: discover → rank → validate
        ...
```

### Models

```python
@dataclass
class NewsItem:
    source_id: str
    title: str
    url: str
    summary: str = ""

@dataclass
class BriefCard:
    rank: int  # 1-10
    title: str
    url: str
    why_it_matters: str

@dataclass
class DailyBrief:
    date: str
    theme: str
    cards: List[BriefCard]  # Exactly 10
    schema_version: str = "1.0"
```

---

## Choosing a Backend

| Backend | Best For | Speed | Quality | Setup |
|---------|----------|-------|---------|-------|
| **fully_scripted** | Offline, testing, baseline | ⚡⚡⚡ Fast | ⭐⭐ | None |
| **google_adk** | Production, Gemini API | ⚡⚡ Medium | ⭐⭐⭐⭐ | API key |
| **ollama_agent** | Learning, local, LangChain | ⚡ Slow | ⭐⭐⭐ | LangChain + Ollama |

---

## LangChain + Ollama Pattern

The ollama_agent uses LangChain's **ReAct** pattern with **AgentExecutor**:

```python
# 1. Define tools with @tool decorator
@tool
def discover(count: int = 100) -> str:
    """Discover stories."""
    return json.dumps([...])

# 2. Initialize LLM + Agent
llm = ChatOllama(model="qwen2.5-coder:14b")
agent = create_react_agent(llm, [discover, rank, validate], prompt)
executor = AgentExecutor(agent=agent, tools=[...])

# 3. Run loop (framework handles Thought→Action→Observation)
result = executor.invoke({"input": "Generate brief"})
```

See [LANGCHAIN_QUICK_REFERENCE.md](../LANGCHAIN_QUICK_REFERENCE.md) for details.

---

## Troubleshooting

**"GEMINI_API_KEY not set"**
```bash
export GEMINI_API_KEY="your-key"
python -m src.google_adk.runner
```

**"Ollama connection refused"**
```bash
# Start Ollama in another terminal
ollama serve

# Then run agent
python -m src.ollama_agent.runner
```

**"No module named langchain"**
```bash
pip install langchain langchain-ollama langchain-core
```

---

## Next Steps

- [ ] Add source_discovery skill integration (60+ sources)
- [ ] Add LLM-based ranking for Ollama (ReAct with reasoning)
- [ ] Add memory/conversation history (optional, for multi-turn)
- [ ] Package for Kaggle submission
- [ ] Add observability (callbacks, tracing)

---

## Files

- [ARCHITECTURE.md](../ARCHITECTURE.md) — Full design reference
- [LANGCHAIN_QUICK_REFERENCE.md](../LANGCHAIN_QUICK_REFERENCE.md) — LangChain patterns
- [LANGCHAIN_OLLAMA_DESIGN.md](../LANGCHAIN_OLLAMA_DESIGN.md) — Detailed design
- [SKILLS_CALLING_STRATEGY.md](../SKILLS_CALLING_STRATEGY.md) — How each backend calls skills
