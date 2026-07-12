# Day 3 Example - ADK Lifecycle Codelab (Clean Capture)

Source codelab:
https://codelabs.developers.google.com/agents-cli-adk-lifecycle

## Scope Captured

This capture focuses on Step 5, "Explore the Agent Code", and summarizes the core ADK 2.0 workflow concepts in a clean format.

## Codelab Navigation

1. Overview
2. Set up Authentication and Environment
3. Set up Agents CLI and Skills
4. Create your Agent Project
5. Explore the Agent Code
6. Automated Linting
7. Interactive Testing with the Playground
8. Command Line Execution
9. Cleanup
10. Summary and Next Steps

## Clean Prompt (from Step 5)

Use this prompt in Antigravity IDE:

"Read and explain the project structure of my new agent project. Walk me through how app/agent.py is configured, highlighting the role of tools, nodes, edges, and the root Workflow."

## Cleaned Example Structure (Representative)

```python
from __future__ import annotations

from typing import Any, Literal

from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events.event import Event
from google.adk.workflow import Edge, Workflow
from google.adk.workflow.agents.llm_agent import LlmAgent
from google.adk.workflow.node import node
from pydantic import BaseModel, Field


class InquiryCategory(BaseModel):
    category: Literal["shipping", "unrelated"] = Field(
        description=(
            "Determine if the user query is related to shipping "
            "or unrelated."
        )
    )


def save_query(node_input: str):
    yield Event(data=node_input, state={"user_query": node_input})


categorize_agent = LlmAgent(
    name="categorize",
    model="gemini-3.1-flash-lite",
    instruction="You are an expert classifier. Categorize the user query.",
    output_key="inquiry_category",
    output_schema=InquiryCategory,
)


@node
def route_inquiry(ctx: Context, node_input: Any):
    category_data = ctx.state.get("inquiry_category", {})
    category = category_data.get("category", "unrelated")
    query = ctx.state.get("user_query", "")
    yield Event(data=query, route=category)


faq_agent = LlmAgent(
    name="shipping_faq",
    model="gemini-3.1-flash-lite",
    instruction="Answer only questions related to shipping FAQ.",
)


@node
def handle_unrelated(ctx: Context, node_input: Any):
    yield Event(
        data=(
            "I am a shipping support assistant and can only answer "
            "shipping FAQ questions."
        )
    )


root_agent = Workflow(
    name="customer_support_workflow",
    edges=[
        *Edge.chain("START", save_query, categorize_agent, route_inquiry),
        (route_inquiry, faq_agent, "shipping"),
        (route_inquiry, handle_unrelated, "unrelated"),
    ],
)

app = App(name="customer_support_agent", root_agent=root_agent)
```

## Key Concepts (Clean Summary)

1. Workflow and Edges
- `Workflow` defines graph orchestration.
- `edges` define linear and conditional flow from `START`.

2. LlmAgent
- Declarative LLM nodes with model, instruction, and optional output schema.

3. Nodes and Context
- `@node` functions perform logic and routing.
- `Context` exposes shared state across steps.
- `Event` passes data, state updates, and route labels.

4. Root App Wrapper
- `App` wraps the root workflow for local playground and runtime tools.

## Day 3 Relevance to This Kaggle POC

Map this pattern into our Day 3 artifacts:

1. Graph-style phase model
- ingest -> normalize -> dedupe/score -> validate -> render

2. Explicit state
- run state and task state in `day_3/state_model.md`

3. Structured outputs
- contracts in `day_3/artifact_contracts.md`

4. Deterministic gates
- validation and baseline comparison before publish

## Notes

Generated ADK code can differ by scaffold/template version. Preserve concepts, not exact formatting.

## Interactive Testing with Playground (Step 7 - Clean Capture)

The local web playground is the fastest way to verify behavior and routing.

Prompt in Antigravity:

"Launch the local development playground for my agent."

Expected behavior:

1. Antigravity starts local server via `agents-cli playground`.
2. Open URL (usually): `http://127.0.0.1:8080/dev-ui/?app=app`
3. Select `app` in the UI and begin interactive testing.

### Baseline Test Prompts

Shipping-path prompt:

"How much is standard shipping?"

Expected:

1. query categorized as shipping
2. routed to `faq_agent`
3. response returned from shipping FAQ behavior

Unrelated-path prompt:

"What is the weather like?"

Expected:

1. query categorized as unrelated
2. routed to `handle_unrelated`
3. polite decline response returned

## Real-Time Auto-Reload Test (Clean Procedure)

1. Modify `faq_agent` instruction in `app/agent.py`.
2. Re-run shipping prompt in the same playground session.
3. Confirm response reflects updated instruction without manual server restart.

Suggested prompt for edit:

"Modify the faq_agent instruction in app/agent.py to make shipping-rate responses more playful and enthusiastic. Add emojis and highlight the free-shipping threshold."

Validation prompt after edit:

"How much is standard shipping?"

Expected validation:

1. response style changes immediately
2. workflow routing still correct
3. no server restart required
