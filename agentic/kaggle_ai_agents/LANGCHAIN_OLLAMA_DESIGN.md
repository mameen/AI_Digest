# LangChain + Ollama Agent Design

Learning LangChain patterns for the ollama_agent backend. This document explains why LangChain, tool definitions, agent orchestration, and comparison with custom ReAct.

## Why LangChain for ollama_agent?

**LangChain solves:**
- ✅ **Tool use loop** — AgentExecutor handles Thought→Action→Observation repeats
- ✅ **Tool parsing** — Auto-extracts tool calls from LLM response
- ✅ **Error handling** — Retries, timeouts, malformed responses
- ✅ **Memory** — Optional conversation history without manual state
- ✅ **Observability** — Built-in logging, tracing via callbacks
- ✅ **Production patterns** — LCEL (LangChain Expression Language) for composability

**vs custom ReAct:**
- ❌ Custom: You manage loop, parsing, error handling
- ✅ LangChain: Framework handles orchestration, you define tools + prompt

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ ollama_agent/agent.py                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  OllamaAgent (inherits base.Agent)                              │
│  ├─ __init__(model, host)                                       │
│  ├─ _init_llm()  → Ollama via LangChain Ollama chat model       │
│  ├─ _init_tools() → Bind discover, rank, validate as Tools     │
│  ├─ _run_agent()  → AgentExecutor loop                          │
│  ├─ discover() → calls tool                                      │
│  ├─ rank() → calls tool                                          │
│  ├─ validate() → calls tool                                      │
│  └─ run() → forwards discover→rank→validate                     │
│                                                                   │
│  System prompt: "You are an AI curator. Use tools to:           │
│    1. discover(count=100) — get recent stories                   │
│    2. rank(items, count=10) — rank by importance                │
│    3. validate(cards) — check output schema"                    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
          ↓ calls ↓
┌─────────────────────────────────────────────────────────────────┐
│ LangChain AgentExecutor Loop                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. prompt + tools → Ollama                                      │
│  2. Ollama: "Thought: I need to discover stories first"         │
│     Action: tool_call(discover, count=100)                      │
│  3. AgentExecutor: Parse action → call discover()               │
│  4. Observation: [100 NewsItem]                                 │
│  5. Repeat: "Now rank these..."                                 │
│     Action: tool_call(rank, items=[...], count=10)              │
│  6. etc. until tool_call(finish) or max iterations              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tool Definitions (LangChain Pattern)

**Option 1: @tool decorator (recommended for simplicity)**

```python
from langchain.tools import tool

@tool
def discover(count: int = 100) -> str:
    """Discover recent AI/ML stories.
    
    Args:
        count: Number of stories to retrieve (default 100)
    
    Returns:
        JSON string with [NewsItem, ...]
    """
    items = source_discovery_skill.fetch(limit=count)
    # Return JSON so LLM can read it
    return json.dumps([dataclasses.asdict(item) for item in items])

@tool
def rank(items_json: str, count: int = 10) -> str:
    """Rank stories by importance.
    
    Args:
        items_json: JSON array of NewsItem
        count: Number of top stories to return (default 10)
    
    Returns:
        JSON string with ranked [NewsItem, ...] (top `count`)
    """
    items = [NewsItem(**item) for item in json.loads(items_json)]
    ranked = ranking_skill.rank(items)
    return json.dumps([dataclasses.asdict(item) for item in ranked[:count]])

@tool
def validate(cards_json: str) -> str:
    """Validate and finalize brief.
    
    Args:
        cards_json: JSON array of BriefCard
    
    Returns:
        JSON string with DailyBrief (10 cards, schema_version, date, theme)
    """
    cards = [BriefCard(**card) for card in json.loads(cards_json)]
    brief = validation_skill.validate(cards)
    return json.dumps(dataclasses.asdict(brief))
```

**Option 2: Tool class (more control)**

```python
from langchain.tools import Tool

def discover_impl(count: int = 100) -> str:
    """Implementation"""
    return json.dumps(...)

discover_tool = Tool(
    name="discover",
    func=discover_impl,
    description="Discover recent AI/ML stories. Returns JSON array of NewsItem.",
)
```

---

## Agent Initialization (LangChain Pattern)

```python
from langchain_ollama import ChatOllama  # pip install langchain-ollama
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate

class OllamaAgent(base.Agent):
    def __init__(self, model: str = "qwen2.5-coder:14b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.llm = None
        self.executor = None
        self._init_llm()
        self._init_agent()
    
    def _init_llm(self):
        """Initialize Ollama via LangChain ChatOllama wrapper."""
        self.llm = ChatOllama(
            model=self.model,
            base_url=self.host,
            temperature=0.7,
            top_k=40,
            top_p=0.9,
        )
    
    def _init_agent(self):
        """Initialize ReAct agent with tools."""
        # Define tools (use @tool decorated functions above)
        tools = [discover, rank, validate]
        
        # System prompt
        prompt = PromptTemplate.from_template("""
You are an AI curator for AI/ML stories. Your task:
1. Discover recent stories using the discover tool
2. Rank them by importance using the rank tool
3. Validate the output and finalize using the validate tool

Think step by step (Thought), then use tools (Action).
When you have the final brief (10 validated cards), return it.

Tools available:
- discover(count=100): Get recent stories
- rank(items_json, count=10): Rank by importance
- validate(cards_json): Finalize and validate brief

Begin!
{agent_scratchpad}
        """)
        
        # Create ReAct agent
        agent = create_react_agent(self.llm, tools, prompt)
        
        # Wrap in executor (handles loop, retries, max iterations)
        self.executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,  # Set False in production
            max_iterations=10,  # Prevent infinite loops
            handle_parsing_errors=True,
        )
    
    def run(self) -> DailyBrief:
        """Run agent and return DailyBrief."""
        result = self.executor.invoke({
            "input": "Generate a top-10 AI/ML stories brief for today."
        })
        
        # Extract DailyBrief from result
        brief_json = result.get("output")
        brief_dict = json.loads(brief_json)
        return DailyBrief(**brief_dict)
```

---

## Agent Execution Flow

```
User calls: agent.run()
    ↓
executor.invoke({"input": "Generate brief..."})
    ↓
LLM receives: system prompt + tools + input
    ↓
LLM responds: "Thought: I need to discover stories first
               Action: discover
               Action Input: {count: 100}"
    ↓
AgentExecutor parses Action/Action Input
    ↓
Calls discover(count=100) → returns [100 NewsItem as JSON]
    ↓
LLM sees Observation: [long JSON]
    ↓
LLM responds: "Thought: Now I'll rank these
               Action: rank
               Action Input: {items_json: [...], count: 10}"
    ↓
Calls rank(items_json, count=10) → returns [10 ranked NewsItem as JSON]
    ↓
LLM: "Thought: Finally validate
      Action: validate
      Action Input: {cards_json: [...]}"
    ↓
Calls validate(cards_json) → returns DailyBrief JSON
    ↓
LLM: "Action: finish
      Action Input: {brief: {...}}"
    ↓
AgentExecutor stops, returns executor result
    ↓
agent.run() extracts DailyBrief and returns
```

---

## Key LangChain Concepts

### 1. **LCEL (LangChain Expression Language)**
Chain components composably:
```python
chain = prompt | llm | parser
chain.invoke({"input": "..."})
```

### 2. **Tool Binding**
LLM knows which tools are available:
```python
llm_with_tools = llm.bind_tools(tools)
```

### 3. **AgentExecutor**
Orchestrates the loop:
- Calls LLM
- Parses tool use from response
- Executes tool
- Feeds observation back to LLM
- Repeats until done/max_iterations

### 4. **Memory (Optional)**
For multi-turn conversations:
```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory()
agent_executor = AgentExecutor(..., memory=memory)
```
(For daily brief, not needed — each run is independent.)

### 5. **Callbacks for Observability**
```python
from langchain.callbacks import StdOutCallbackHandler

executor = AgentExecutor(
    ...,
    callbacks=[StdOutCallbackHandler()]  # Logs all steps
)
```

---

## Comparison: LangChain vs Custom ReAct

| Aspect | Custom ReAct | LangChain |
|--------|------------|-----------|
| **Loop logic** | You write it | AgentExecutor handles |
| **Tool parsing** | Regex or manual | Built-in, robust |
| **Error handling** | You implement | Automatic retries, timeout handling |
| **Lines of code** | 200+ | 80-100 |
| **Learning curve** | Lower (but fragile) | Higher (but production-ready) |
| **Memory** | Manual state dict | Optional memory classes |
| **Debugging** | Print statements | Callbacks + tracing |
| **Production readiness** | No | Yes |

---

## File Structure for ollama_agent with LangChain

```
src/ollama_agent/
├── __init__.py
├── agent.py           # OllamaAgent with LangChain AgentExecutor
├── tools.py           # @tool decorated functions (discover, rank, validate)
├── config.py          # Config loading
├── README.md          # Setup + usage
└── requirements.txt   # langchain, langchain-ollama, ...
```

**requirements.txt:**
```
langchain>=0.1.0
langchain-ollama>=0.0.1
langchain-core>=0.1.0
ollama>=0.1.0
```

---

## Setup & Usage

**1. Install dependencies:**
```bash
pip install langchain langchain-ollama langchain-core
```

**2. Verify Ollama running:**
```bash
curl http://localhost:11434/api/tags
```

**3. Run agent:**
```python
from src.ollama_agent.agent import OllamaAgent

agent = OllamaAgent(model="qwen2.5-coder:14b")
brief = agent.run()
print(brief)
```

**4. Enable verbose logging:**
```python
executor.verbose = True  # Prints all Thought/Action/Observation steps
```

---

## Common Pitfalls & Solutions

| Problem | Cause | Solution |
|---------|-------|----------|
| "Tool not called" | LLM doesn't know tool exists | Check tool descriptions are clear |
| "Parsing error" | LLM format doesn't match expected | Set `handle_parsing_errors=True` |
| "Infinite loop" | LLM repeats same action | Set `max_iterations=10` |
| "Ollama timeout" | Model too slow | Reduce prompt verbosity, increase timeout |
| "Invalid JSON from tool" | Tool returns non-JSON | Always wrap return values in `json.dumps()` |

---

## Resources

- [LangChain Agent Concepts](https://python.langchain.com/docs/concepts/agents/)
- [ReAct Agent Pattern](https://python.langchain.com/docs/tutorials/agents/)
- [ChatOllama Integration](https://python.langchain.com/docs/integrations/chat/ollama/)
- [Tool Definitions](https://python.langchain.com/docs/how_to/custom_tools/)

---

## Next Steps

1. ✅ Understand LangChain agents (this doc)
2. ⏳ Create `src/ollama_agent/tools.py` with @tool functions
3. ⏳ Create `src/ollama_agent/agent.py` with OllamaAgent class
4. ⏳ Create `src/ollama_agent/README.md` with setup steps
5. ⏳ Test: `python -m src.ollama_agent.agent`
