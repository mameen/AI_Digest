# Skills Calling Strategy — 3 Implementations

How each backend calls the shared skills (discover, rank, validate).

---

## Summary Table

| Backend | Tool Discovery | Skill Calling | Framework | Lines of Code |
|---------|----------------|---------------|-----------|---|
| **fully_scripted** | None (direct) | Direct `import`+`call` | None | ~80 |
| **google_adk** | ADK registry (`.instructions.md`) | ADK framework routes to skill functions | Google ADK | ~120 |
| **ollama_agent** | LangChain `@tool` decorator | LangChain `AgentExecutor` loop | LangChain | ~120 |

---

## 1. fully_scripted — Direct Calling

**Pattern:** Procedural, no framework, pure function calls.

**How it works:**
```python
# runner.py
from src.fully_scripted.skills import discoverer, ranker, validator

items = discoverer.find_items()  # Direct call
ranked = ranker.rank(items)      # Direct call
brief = validator.validate(ranked)  # Direct call
```

**Pros:**
- ✅ Simple to understand
- ✅ No dependencies beyond stdlib
- ✅ Fast baseline
- ✅ Easy to debug

**Cons:**
- ❌ No agent orchestration
- ❌ No LLM reasoning
- ❌ Hardcoded order (discover → rank → validate)

**When to use:** Offline MVP, keyword-based ranking tests, performance baseline.

---

## 2. google_adk — ADK Framework Routing

**Pattern:** Framework-driven tool discovery and dispatch.

**How it works:**

**a) Tool Definition** (in `agent.py`):
```python
class GoogleADKAgent(base.Agent):
    def discover(self) -> List[NewsItem]:
        """Tool: Discover recent stories."""
        return source_discovery_skill.fetch(limit=100)
    
    def rank(self, items: List[NewsItem]) -> List[NewsItem]:
        """Tool: Rank by importance using Gemini."""
        # Call Gemini API
        return gemini_ranker.rank(items, count=10)
    
    def validate(self, items: List[NewsItem]) -> DailyBrief:
        """Tool: Validate schema."""
        return validator.validate(items)
```

**b) Registration** (in `.instructions.md`):
```
## Tools

### discover
Discover recent AI/ML stories.
- Called when: agent needs source material
- Returns: List[NewsItem]

### rank
Rank stories by importance.
- Called when: agent has collected items
- Returns: List[NewsItem] (top 10)

### validate
Validate and finalize brief.
- Called when: ready to output
- Returns: DailyBrief (10 cards, schema version 1.0)
```

**c) ADK Framework Load & Dispatch:**
```
ADK Runtime:
1. Load agent.py
2. Parse .instructions.md
3. Discover tool methods: discover(), rank(), validate()
4. User calls: agent.forward()
5. ADK calls: agent.discover() → agent.rank() → agent.validate()
6. Returns: DailyBrief
```

**Pros:**
- ✅ ADK-compliant (portable to Google Agent APIs)
- ✅ Framework handles orchestration
- ✅ Tool discovery automatic
- ✅ Production-ready

**Cons:**
- ❌ Tied to Google ADK
- ❌ Requires Gemini API key
- ❌ Less transparent control flow

**When to use:** Production deployment, Gemini integration, Google agent ecosystem.

---

## 3. ollama_agent — LangChain Tool Binding

**Pattern:** Framework-driven via LangChain AgentExecutor + ReAct loop.

**How it works:**

**a) Tool Definition** (in `tools.py`):
```python
from langchain.tools import tool

@tool
def discover(count: int = 100) -> str:
    """Discover recent AI/ML stories.
    
    Args:
        count: Number of stories to retrieve
    
    Returns:
        JSON array of NewsItem
    """
    items = source_discovery_skill.fetch(limit=count)
    return json.dumps([dataclasses.asdict(i) for i in items])

@tool
def rank(items_json: str, count: int = 10) -> str:
    """Rank stories by importance.
    
    Args:
        items_json: JSON array of NewsItem
        count: Number of top stories
    
    Returns:
        JSON array of ranked NewsItem
    """
    items = [NewsItem(**i) for i in json.loads(items_json)]
    ranked = ollama_ranker.rank(items)
    return json.dumps([dataclasses.asdict(i) for i in ranked[:count]])

@tool
def validate(cards_json: str) -> str:
    """Validate and finalize brief.
    
    Args:
        cards_json: JSON array of BriefCard
    
    Returns:
        DailyBrief JSON
    """
    cards = [BriefCard(**c) for c in json.loads(cards_json)]
    brief = validator.validate(cards)
    return json.dumps(dataclasses.asdict(brief))
```

**b) Agent Initialization** (in `agent.py`):
```python
from langchain_ollama import ChatOllama
from langchain.agents import create_react_agent, AgentExecutor
from src.ollama_agent.tools import discover, rank, validate

class OllamaAgent(base.Agent):
    def __init__(self, model: str = "qwen2.5-coder:14b"):
        self.llm = ChatOllama(model=model, base_url="http://localhost:11434")
        tools = [discover, rank, validate]  # @tool decorated
        
        prompt = PromptTemplate.from_template("""
You are an AI curator. Use tools to:
1. discover() — get recent stories
2. rank() — rank by importance
3. validate() — finalize brief

Reason step-by-step. When ready, call validate() for final output.
{agent_scratchpad}
        """)
        
        agent = create_react_agent(self.llm, tools, prompt)
        self.executor = AgentExecutor(agent=agent, tools=tools, max_iterations=10)
    
    def run(self) -> DailyBrief:
        """Run agent loop."""
        result = self.executor.invoke({
            "input": "Generate top-10 AI/ML stories brief for today."
        })
        brief_dict = json.loads(result["output"])
        return DailyBrief(**brief_dict)
```

**c) Execution Flow:**
```
executor.invoke({"input": "Generate brief..."})
    ↓
LLM: "Thought: I need to discover stories first.
      Action: discover
      Action Input: {count: 100}"
    ↓
AgentExecutor parses Action → calls discover(count=100)
    ↓
Observation: [100 NewsItem as JSON]
    ↓
LLM: "Thought: Now rank them.
      Action: rank
      Action Input: {items_json: [...], count: 10}"
    ↓
AgentExecutor calls rank(...) → [10 ranked items]
    ↓
LLM: "Thought: Validate output.
      Action: validate
      Action Input: {cards_json: [...]}"
    ↓
AgentExecutor calls validate(...) → DailyBrief JSON
    ↓
executor returns {"output": "DailyBrief JSON", ...}
    ↓
agent.run() extracts and returns DailyBrief
```

**Pros:**
- ✅ Production-grade orchestration (framework-managed loop, retries, error handling)
- ✅ LLM drives workflow (LLM decides order, context-aware)
- ✅ Easy to add/remove tools (just add `@tool` function)
- ✅ Offline-safe (Ollama is local)
- ✅ Learning opportunity (master LangChain patterns)
- ✅ Composable (LCEL chains)

**Cons:**
- ❌ Extra dependency (langchain, langchain-ollama)
- ❌ Slightly more complex setup
- ❌ LLM quality matters (weak models may not follow tool instructions)

**When to use:** Learning LangChain, local dev, production agents, flexible workflows.

---

## Comparison: Decision Tree

Choose your backend:

```
Do you need LLM reasoning?
├─ No → fully_scripted (keyword ranking, fast baseline)
└─ Yes:
   Do you have Gemini API key + want ADK integration?
   ├─ Yes → google_adk (ADK-compliant, production)
   └─ No:
      Do you want to learn LangChain?
      ├─ Yes → ollama_agent (LangChain, Ollama local)
      └─ No → Consider Google ADK (but need API key)
```

---

## See Also

- [ARCHITECTURE.md](./ARCHITECTURE.md) — Full folder structure + requirements per backend
- [LANGCHAIN_OLLAMA_DESIGN.md](./LANGCHAIN_OLLAMA_DESIGN.md) — Detailed LangChain patterns, tool definitions, troubleshooting
- [google_adk_instructions.md](./google_adk_instructions.md) — Google ADK agent prompt (reference)
- [ollama_agent_instructions.md](./ollama_agent_instructions.md) — Ollama agent system prompt (reference)
