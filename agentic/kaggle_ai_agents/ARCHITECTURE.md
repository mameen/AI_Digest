# Kaggle AI Digest — Architecture & Implementation Guide

**Date:** 2026-07-12  
**Status:** Refactoring to 3-implementation structure (OOP, composable)  
**Repo:** `agentic/kaggle_ai_agents/`

---

## Folder Hierarchy

```
agentic/kaggle_ai_agents/
├── submission/
│   └── kaggle_submission.ipynb           # FINAL SUBMISSION (33 cells, all passing)
│
├── src/
│   ├── __init__.py
│   │
│   ├── base/                             # Shared abstractions & models
│   │   ├── __init__.py
│   │   ├── agent.py                      # Abstract Agent base class
│   │   ├── skills.py                     # Skill/Tool interface definitions
│   │   ├── models.py                     # Shared: NewsItem, BriefCard, DailyBrief
│   │   └── config.py                     # Configuration management
│   │
│   ├── fully_scripted/                   # **No agents** — direct script calls
│   │   ├── __init__.py
│   │   ├── runner.py                     # Main entry: Orchestrates skill calls
│   │   ├── skills/
│   │   │   ├── discoverer.py             # Fetch RSS feeds (arXiv, fallback)
│   │   │   ├── ranker.py                 # Keyword-based scoring (no LLM)
│   │   │   └── validator.py              # Schema validation
│   │   ├── config.py                     # fully_scripted config
│   │   └── README.md                     # How to run
│   │
│   ├── google_adk/                       # **ADK-compliant** — Google Gemini backend
│   │   ├── __init__.py
│   │   ├── agent.py                      # GoogleADKAgent (inherits Agent base)
│   │   ├── skills/
│   │   │   ├── discoverer.py             # Fetch via source_discovery skill
│   │   │   ├── ranker.py                 # Gemini API ranker
│   │   │   └── validator.py              # Schema validation
│   │   ├── config.py                     # Google ADK config
│   │   ├── .instructions.md              # ADK instructions (loaded by framework)
│   │   ├── agent_instructions.md         # Human-readable agent prompt
│   │   └── README.md                     # How to run
│   │
│   └── ollama_agent/                     # **LangChain agent** — Ollama LLM backend
│       ├── __init__.py
│       ├── agent.py                      # OllamaAgent (uses LangChain AgentExecutor)
│       ├── tools.py                      # @tool decorated functions (discover, rank, validate)
│       ├── skills/
│       │   ├── discoverer.py             # Fetch via source_discovery skill
│       │   ├── ranker.py                 # Ollama HTTP ranker (called by tool)
│       │   └── validator.py              # Schema validation
│       ├── config.py                     # Ollama config (model, host, etc.)
│       ├── agent_instructions.md         # Agent system prompt
│       ├── requirements.txt              # langchain, langchain-ollama, langchain-core
│       └── README.md                     # How to run + LangChain setup
│
├── config/
│   ├── project.yaml                      # Source registry (60+ sources)
│   ├── fully_scripted.yaml               # fully_scripted backend config
│   ├── google_adk.yaml                   # Google ADK config
│   └── ollama_agent.yaml                 # Ollama agent config
│
├── skills/
│   ├── source_discovery/                 # Multi-source fetcher (shared)
│   │   ├── SKILL.md
│   │   └── scripts/discover.py
│   ├── dedupe_and_rank/                  # Dedup + rank (shared)
│   │   ├── SKILL.md
│   │   └── scripts/rank.py
│   └── artifact_validation/              # Schema validation (shared)
│       ├── SKILL.md
│       └── scripts/validate.py
│
├── run.py                                # DEPRECATED — will be removed
├── google_adk_instructions.md            # Google ADK agent prompt (reference)
├── ollama_agent_instructions.md          # Ollama agent prompt (reference)
├── README.md                             # Project overview
└── ARCHITECTURE.md                       # This file
```

---

## Implementation Profiles

### 1. `fully_scripted/` — No Agent Framework

**Purpose:** Fast baseline for comparison  
**Backend:** Pure Python (no LLM)  
**Framework:** None  
**Orchestration:** Direct function calls

**High-Level Requirements:**
```
Python 3.9+
├── stdlib: urllib, xml.etree, json, os, sys
├── skill scripts: source_discovery, dedupe_and_rank, artifact_validation
└── data flow: discover() → rank() → validate() → DailyBrief
```

**Key Files:**
- `runner.py` — Main orchestrator (no agent class needed)
- `skills/discoverer.py` — RSS parser (stdlib only)
- `skills/ranker.py` — Keyword-based scoring
- `skills/validator.py` — Schema check

**Data Flow:**
```
fetch_items() → [NewsItem, ...]
    ↓
rank_script() → [ranked NewsItem, ...]
    ↓
validate() → DailyBrief(10 cards)
```

**When to use:** Quick testing, no network calls, deterministic output

---

### 2. `google_adk/` — Google ADK Agent

**Purpose:** Production-ready agent following ADK patterns  
**Backend:** Google Gemini API  
**Framework:** Google Agent Development Kit (ADK)  
**Orchestration:** ADK agent framework (skill discovery, tool dispatch)

**High-Level Requirements:**
```
Python 3.9+
├── stdlib: urllib, json, os, sys
├── google-generativeai (Gemini API)
├── ADK framework (if available)
├── skill scripts: source_discovery, dedupe_and_rank, artifact_validation
├── .instructions.md (ADK prompt)
└── agent_instructions.md (reference)
```

**Key Files:**
- `agent.py` — `GoogleADKAgent` class (inherits `Agent` base)
- `skills/discoverer.py` — Calls source_discovery skill script
- `skills/ranker.py` — Calls Gemini API via generativeai
- `skills/validator.py` — Schema check
- `.instructions.md` — ADK-compliant instructions (framework loads)
- `agent_instructions.md` — Human-readable (reference only)

**Data Flow:**
```
ADK Framework
├── Load .instructions.md
├── Register tools: discover, rank, validate
└── Agent loop:
    discover() → source_discovery skill → [NewsItem, ...]
        ↓
    rank() → Gemini API → [ranked NewsItem, ...]
        ↓
    validate() → schema check → DailyBrief(10 cards)
```

**When to use:** Production deployment, ADK integration, Gemini API available

**Environment:**
```bash
export GEMINI_API_KEY="your-api-key"
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json" # optional
```

---

### 3. `ollama_agent/` — LangChain + ReAct Agent

**Purpose:** Standalone local LLM agent with production-grade orchestration  
**Backend:** Local Ollama LLM  
**Framework:** LangChain (AgentExecutor + ReAct pattern)  
**Orchestration:** Framework-managed tool loop

**High-Level Requirements:**
```
Python 3.9+
├── LangChain: langchain, langchain-ollama, langchain-core
├── Ollama running (localhost:11434 or remote)
├── Ollama model: qwen2.5-coder:14b (default, 9 GB M3 Mac)
├── skill scripts: source_discovery, dedupe_and_rank, artifact_validation
└── agent_instructions.md (system prompt for LLM)
```

**Key Files:**
- `agent.py` — `OllamaAgent` class (inherits `base.Agent`)
  - Uses LangChain `ChatOllama` for LLM
  - `AgentExecutor` manages tool loop + retries + error handling
  - ~120 lines, production-ready
- `tools.py` — @tool decorated functions
  - `discover(count: int)` → calls source_discovery skill
  - `rank(items_json: str, count: int)` → LLM-based ranking
  - `validate(cards_json: str)` → schema validation
- `skills/discoverer.py` — Calls source_discovery skill script
- `skills/ranker.py` — Ollama HTTP ranker (via LangChain)
- `skills/validator.py` — Schema validation
- `agent_instructions.md` — System prompt (loaded by LangChain)

**Data Flow:**
```
LangChain AgentExecutor ReAct Loop:
1. Initialize: ChatOllama + @tool decorated functions
2. LLM receives: system_prompt + tools + input
3. LLM responds: "Thought: I need to discover stories
                  Action: discover
                  Action Input: {count: 100}"
4. AgentExecutor parses Action → calls discover(count=100)
5. Observation: [100 NewsItem as JSON]
6. LLM receives Observation, generates next Action
7. Repeat: rank(items_json, count=10) → [10 ranked items]
8. Repeat: validate(cards_json) → DailyBrief
9. AgentExecutor returns result, extracts DailyBrief
```

**Ollama Model Options (M3 Mac):**
| Model | Size | Speed | Quality | Recommended |
|-------|------|-------|---------|---|
| qwen2.5-coder:14b | 9.0 GB | ⚡ Fast | ⭐⭐⭐ | ✅ DEFAULT |
| qwen3:8b | 5.2 GB | ⚡⚡ Very Fast | ⭐⭐ | Alternative |
| qwen3.6:35b | 23 GB | 🐌 Slow | ⭐⭐⭐⭐ | High quality |

**Learning Goal:**
- Master LangChain patterns: `@tool` decorator, `AgentExecutor`, `PromptTemplate`, tool binding
- Understand ReAct orchestration (framework-managed, not hand-coded)
- See production-grade agent patterns

**When to use:** Local dev, learning LangChain, no API keys, full transparency, offline

**Environment:**
```bash
ollama serve  # Start Ollama
ollama pull qwen2.5-coder:14b  # Download model

# Install LangChain deps
pip install langchain langchain-ollama langchain-core

# Then run agent
python -m src.ollama_agent.agent --model qwen2.5-coder:14b
```

**See also:** [LANGCHAIN_OLLAMA_DESIGN.md](./LANGCHAIN_OLLAMA_DESIGN.md) for detailed patterns, tool definitions, and troubleshooting.

---

## Shared Components

### `base/` — Abstract Base Classes & Models

**Purpose:** DRY principle — all implementations share these

**Files:**
- `agent.py` — Abstract `Agent` class
  ```python
  class Agent(ABC):
      @abstractmethod
      def discover(self) -> List[NewsItem]: ...
      @abstractmethod
      def rank(self, items: List[NewsItem]) -> List[NewsItem]: ...
      @abstractmethod
      def validate(self, items: List[NewsItem]) -> DailyBrief: ...
      def run(self) -> DailyBrief:
          items = self.discover()
          ranked = self.rank(items)
          return self.validate(ranked)
  ```

- `models.py` — Data classes (Pydantic or dataclass)
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

- `skills.py` — Skill interface
  ```python
  class Skill(ABC):
      @abstractmethod
      def execute(self, *args, **kwargs) -> Any: ...
  ```

- `config.py` — Configuration loading
  ```python
  def load_config(backend: str) -> dict:
      # Load from config/<backend>.yaml or env
  ```

### `skills/` — Shared Skill Scripts

**These are called by ALL three implementations:**

1. **source_discovery/scripts/discover.py**
   - Inputs: config.yaml with 60+ sources
   - Outputs: JSON array of NewsItem records
   - Used by: google_adk, ollama_agent (fully_scripted has its own simple parser)

2. **dedupe_and_rank/scripts/rank.py**
   - Inputs: JSON array of NewsItem
   - Outputs: Deduplicated + scored JSON array
   - Used by: fully_scripted (for non-LLM ranking comparison)

3. **artifact_validation/scripts/validate.py**
   - Inputs: DailyBrief JSON
   - Outputs: Pass/Fail + error messages
   - Used by: All three (final schema check)

---

## CLI Entry Points

### `fully_scripted`
```bash
python -m src.fully_scripted.runner [--output brief_output.json]
```

### `google_adk`
```bash
python -m src.google_adk.runner [--output brief_output.json]
```

### `ollama_agent`
```bash
python -m src.ollama_agent.runner \
    --model qwen2.5-coder:14b \
    --host http://localhost:11434 \
    --output brief_output.json
```

---

## Testing & Validation

**Per implementation:**
- Unit tests for each skill
- Integration tests: discover → rank → validate
- Schema validation against DailyBrief
- Fallback behavior (network unavailable)

**Cross-implementation:**
- Compare output JSON schema (must be identical)
- Verify 10 cards exactly
- Verify URLs are HTTPS
- Verify dates are YYYY-MM-DD

---

## Migration Path

**Current state (run.py):**
- Monolithic procedural script
- All logic in one file
- No structure

**Target state:**
- ✅ `base/` — Abstractions (implement first)
- ✅ `fully_scripted/` — Baseline (simple, no agent)
- ✅ `google_adk/` — ADK-compliant (with .instructions.md)
- ✅ `ollama_agent/` — Custom ReAct (hand-coded)
- ✅ `config/` — YAML configs per backend
- ⏹️ `run.py` — Deprecated (remove after migration)

---

## Key Design Principles

1. **Composable:** Each implementation is independent
2. **OOP:** Inherit from `Agent` base class
3. **Testable:** Skill scripts are independently callable
4. **Transparent:** All code visible, no hidden framework magic
5. **Reversible:** Can swap implementations via CLI flag
