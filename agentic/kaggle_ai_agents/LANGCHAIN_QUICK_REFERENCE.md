# LangChain Quick Reference — AI Digest Agent

TL;DR for implementing `ollama_agent` with LangChain.

---

## Installation

```bash
pip install langchain langchain-ollama langchain-core
```

---

## 1. Define Tools (@tool decorator)

```python
from langchain.tools import tool
import json

@tool
def discover(count: int = 100) -> str:
    """Discover stories. Returns JSON."""
    items = [...]  # fetch items
    return json.dumps([...])

@tool
def rank(items_json: str, count: int = 10) -> str:
    """Rank stories. Returns JSON."""
    items = json.loads(items_json)
    ranked = [...]  # rank
    return json.dumps([...])

@tool
def validate(cards_json: str) -> str:
    """Validate brief. Returns DailyBrief JSON."""
    brief = [...]  # validate
    return json.dumps([...])
```

**Key:** Always return `str` (JSON), not Python objects. LLM needs text.

---

## 2. Initialize LLM

```python
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="qwen2.5-coder:14b",
    base_url="http://localhost:11434",
    temperature=0.7,
    top_k=40,
    top_p=0.9,
)
```

**Alternatively (if langchain_ollama not available yet):**
```python
from langchain.llms.ollama import Ollama

llm = Ollama(
    model="qwen2.5-coder:14b",
    base_url="http://localhost:11434",
)
```

---

## 3. Create Agent

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

# System prompt
prompt = PromptTemplate.from_template("""
You are an AI curator. Use tools to discover, rank, and validate stories.
Think step-by-step. When ready, call validate() to finalize.

Tools: discover, rank, validate

{agent_scratchpad}
""")

# Tools list
tools = [discover, rank, validate]

# Create agent
agent = create_react_agent(llm, tools, prompt)

# Executor (handles loop, retries, max iterations)
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,  # Set False in production
    max_iterations=10,
    handle_parsing_errors=True,
)
```

---

## 4. Run Agent

```python
result = executor.invoke({
    "input": "Generate a top-10 AI/ML stories brief for today."
})

# Extract output
brief_json = result["output"]  # DailyBrief JSON
brief = DailyBrief(**json.loads(brief_json))
```

---

## 5. Full Example

```python
from langchain.tools import tool
from langchain_ollama import ChatOllama
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
import json

# ── Tools ────────────────────────────────────────────

@tool
def discover(count: int = 100) -> str:
    """Discover recent AI/ML stories."""
    # Mock data for demo
    items = [
        {"source_id": "arxiv", "title": "LLMs Achieve New Benchmark", "url": "https://arxiv.org/abs/...", "summary": "..."}
    ]
    return json.dumps(items)

@tool
def rank(items_json: str, count: int = 10) -> str:
    """Rank stories by importance."""
    items = json.loads(items_json)
    # Return top `count` (mock: just take first N)
    return json.dumps(items[:count])

@tool
def validate(cards_json: str) -> str:
    """Validate brief."""
    cards = json.loads(cards_json)
    brief = {
        "date": "2026-07-12",
        "theme": "AI signal",
        "cards": cards,
        "schema_version": "1.0"
    }
    return json.dumps(brief)

# ── Agent ────────────────────────────────────────────

llm = ChatOllama(
    model="qwen2.5-coder:14b",
    base_url="http://localhost:11434",
)

prompt = PromptTemplate.from_template("""
You are an AI curator. 
1. Use discover() to get stories
2. Use rank() to rank them
3. Use validate() to finalize

{agent_scratchpad}
""")

tools = [discover, rank, validate]

agent = create_react_agent(llm, tools, prompt)

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=10,
    handle_parsing_errors=True,
)

# ── Run ──────────────────────────────────────────────

result = executor.invoke({
    "input": "Generate a brief of top 10 AI/ML stories."
})

print(result["output"])
```

---

## Common Patterns

### Pattern 1: Add Memory (for multi-turn)
```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory()
executor = AgentExecutor(agent=agent, tools=tools, memory=memory)
```

### Pattern 2: Add Callbacks (logging)
```python
from langchain.callbacks import StdOutCallbackHandler

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[StdOutCallbackHandler()]  # Logs all steps
)
```

### Pattern 3: Custom Tool (no @tool)
```python
from langchain.tools import Tool

def my_func(x: int) -> str:
    return str(x * 2)

my_tool = Tool(
    name="double",
    func=my_func,
    description="Double a number"
)
```

### Pattern 4: Tool with Error Handling
```python
@tool
def risky_tool(x: int) -> str:
    """Do something risky."""
    try:
        result = 10 / x  # May fail if x=0
        return json.dumps({"result": result})
    except ZeroDivisionError:
        return json.dumps({"error": "Division by zero"})
```

---

## Debugging

**See what LLM is thinking:**
```python
executor.verbose = True  # Prints Thought/Action/Observation
```

**Capture LLM output:**
```python
result = executor.invoke({"input": "..."})
print(result["output"])  # Final output
print(result["intermediate_steps"])  # All actions taken
```

**Test tool directly:**
```python
from langchain.tools import tool

@tool
def my_tool(x: int) -> str:
    return str(x)

# Call directly
print(my_tool(42))  # Works as normal function
```

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "Tool not found" | LLM doesn't use tool | Check tool description clarity |
| "Parsing error" | Format mismatch | Set `handle_parsing_errors=True` |
| "Infinite loop" | LLM repeats same action | Increase `max_iterations`, clarify prompt |
| "Ollama timeout" | Model too slow | Use smaller model, reduce prompt size |
| "Output not JSON" | Tool returns non-JSON | Always wrap in `json.dumps()` |

---

## Resources

- Docs: https://python.langchain.com/docs/concepts/agents/
- ReAct Tutorial: https://python.langchain.com/docs/tutorials/agents/
- Ollama Integration: https://python.langchain.com/docs/integrations/chat/ollama/
- Tool Definitions: https://python.langchain.com/docs/how_to/custom_tools/

---

## Next: Implement ollama_agent

Ready to code? Start with:
1. Create `src/ollama_agent/tools.py` — define @tool functions
2. Create `src/ollama_agent/agent.py` — initialize LLM + executor
3. Test: `python -m src.ollama_agent.agent`

See [LANGCHAIN_OLLAMA_DESIGN.md](./LANGCHAIN_OLLAMA_DESIGN.md) for full reference.
