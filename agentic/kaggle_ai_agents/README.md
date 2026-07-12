# Kaggle AI Agents Capstone Project

A standalone five-day learning project for the Kaggle **AI Agents: Intensive Vibe Coding Capstone Project**.

**5-Day AI Agents: Intensive Vibe Coding Course With Google**
https://www.kaggle.com/competitions/5-day-ai-agents-intensive-vibecoding-course-with-google


**Competition:**  
https://www.kaggle.com/competitions/vibecoding-agents-capstone-project

## Purpose

This project applies the concepts from Kaggle and Google’s five-day AI Agents course through a small, practical agent-based application.

The project will be designed, implemented, evaluated, documented, and prepared for demonstration over five development days.

All hackathon-specific code, notes, tests, examples, assets, and submission materials will remain inside this directory.

## Quick Reference

Common tasks — run evals, add a skill, add a source, run tests:
[`HOWTO.md`](HOWTO.md)

---

## Before You Start: Assessment Checklist

**This section helps you assess whether your team and infrastructure are ready to run and evaluate the PoC.**

### 👥 Team Requirements

| Role | Skills | Must-Have | Time |
|------|--------|-----------|------|
| Python Developer | Python 3.11+, pytest, CLI, Git | ✅ Required | 2-4 hrs |
| QA / Verifier | Can read JSON, verify schema | ✅ Required | 1-2 hrs |
| DevOps (optional) | Docker/Ollama | ⭕ If using Ollama backend | 30min |
| LLM Researcher (optional) | Prompt engineering | ⭕ If experimenting with LLM | 1-2 hrs |

### 🤖 Infrastructure Requirements

Choose ONE backend. All produce identical `DailyBrief` output:

| Backend | LLM? | Setup | Cost | Best For |
|---------|------|-------|------|----------|
| **direct_script** | ❌ None | 0 min | Free | Testing, CI/CD (pick this to start) |
| **google_adk** | ❌ None | 5 min | Free | Production, course demo (recommended) |
| **ollama** | ✅ Yes | 20-30 min | Free | Research, LLM experimentation |

### ✅ Quick Start (10 minutes)

```bash
# 1. Check Python version
python3 --version          # Should be 3.11+

# 2. Install dependencies
pip install -r requirements-dev.txt

# 3. Run tests
PYTHONPATH=src pytest agentic/kaggle_ai_agents/tests -q
# Should see: "72 passed"

# 4. Generate a brief with stubs (no real sources)
PYTHONPATH=src python -c "
  from kaggle_ai_agents.workflow import run_daily_brief_with_backend
  brief = run_daily_brief_with_backend('direct_script', use_real_sources=False)
  print(f'✅ Generated {len(brief.cards)} cards')
  print(f'✅ Schema valid')
"
```

### 📊 Full Assessment

For the detailed assessment form (team roles, infrastructure choices, evaluation plan):
**See: [`HOWTO.md` — Assessment Section](HOWTO.md#assessment-people--llms-required-to-run--evaluate-the-poc)**

---

## Architecture Shift: From Multi-Agent to Single Agent with Progressive Context

The course highlighted a meaningful shift in how production-grade agents are designed.

### The Old Default: Multi-Agent Graphs

The instinct was to split work across a graph of specialized agents — a researcher, a librarian, a synthesizer — each with a fixed context window and a hand-off step between them.

This is the architecture this repo already runs in production (`agentic/hermes`):

```
concierge → researcher × N → librarian → synthesizer → render
```

It works, but it has real costs:

- each agent re-reads overlapping context at every hand-off
- context rot accumulates across steps — later agents see summaries of summaries
- orchestration adds latency and failure surface
- skills and tools are duplicated or siloed per agent

### The New Model: Single Agent + Progressive Context (Skills-Driven)

The course describes a different approach, enabled by larger context windows and Agent Skills:

- **One agent** handles the full workflow
- **Skills** (`SKILL.md` files) are loaded on demand — only the context the current step needs arrives in the window
- **Progressive disclosure**: broad instruction at the top; detailed tool logic and examples load only when that skill is needed
- **Context stays fresh** because the agent controls what it reads, not a fixed pipeline topology

### Why This Matters for This Project

This Kaggle project is deliberately built as a **single-agent** implementation using this model:

1. `workflow.py` is the one agent driving all phases: ingest → select → validate → render
2. `config/project.yaml` replaces hardcoded source lists — the agent reads config on demand
3. `tools/` modules are skills: each has a clear contract and is loaded only when needed
4. `state.py` tracks phase explicitly so the agent can resume without re-reading history
5. Evaluation and security gates are inline steps, not separate agents

The multi-agent `hermes` pipeline remains the production baseline for parity checks. This project is the simpler, more maintainable single-agent path the course advocates.

## Project Principles

- Build only what can be demonstrated.
- Keep the scope small enough to complete.
- Separate planning, implementation, testing, and submission work.
- Document decisions as they are made.
- Treat external content as untrusted input.
- Keep credentials and private information out of the repository.
- Use deterministic validation where possible.
- Describe only features that are actually implemented.
- Preserve clear setup and reproduction instructions.
- Keep the final project understandable without requiring private infrastructure.

## Five-Day Structure

```text
kaggle_ai_agents/
├── README.md
├── day_1/
├── day_2/
├── day_3/
├── day_4/
├── day_5/
├── src/
├── tests/
├── config/
├── examples/
├── assets/
└── submission/
```

The root `README.md` remains the main project entry point.

Playlist pacing plan (5 videos over 5 days):
[`video_plan.md`](video_plan.md)

The daily folders record the work completed during each stage of the hackathon. Shared application code belongs in `src/`, shared tests belong in `tests/`, and final competition materials belong in `submission/`.

## Day 1 — Problem Definition and Agent Design

### Goal

Choose one clear real-world problem and define the smallest useful agent-based solution.

### Work

- define the target user
- define the problem
- explain why an agent is useful
- identify the minimum complete workflow
- define inputs and outputs
- define success criteria
- identify assumptions
- identify risks
- choose the initial technical approach
- create the first architecture draft
- create the project skeleton

### Deliverables

```text
day_1/
├── README.md
├── problem_statement.md
├── target_user.md
├── use_cases.md
├── scope.md
├── architecture.md
├── success_criteria.md
├── risks.md
└── decisions.md
```

### Completion Criteria

Day 1 is complete when:

- the problem is specific
- the target user is clear
- the scope is small enough to finish
- the initial workflow is documented
- the expected outputs are defined
- success can be measured
- major assumptions and risks are visible

## Day 2 — Tools and Interoperability

### Goal

Connect the agent to the tools and data sources required for the selected use case.

### Work

- define the tools required by the workflow
- define tool inputs and outputs
- create source adapters
- create structured tool responses
- handle timeouts and failures
- handle malformed content
- preserve source metadata
- restrict tools to their intended purpose
- create test fixtures
- verify tool behavior independently

### Deliverables

```text
day_2/
├── README.md
├── tool_inventory.md
├── source_contracts.md
├── data_flow.md
├── failure_handling.md
├── examples/
└── decisions.md
```

### Completion Criteria

Day 2 is complete when:

- each tool has one clear purpose
- tool contracts are documented
- failures are visible
- source metadata is preserved
- tool behavior can be tested without running the full application

## Day 3 — State, Context, and Agent Behavior

### Goal

Define how the agent receives context, maintains state, performs work, and produces reusable artifacts.

### Work

- define the run state
- define the task state
- define context boundaries
- define structured artifacts
- define retry behavior
- define stopping conditions
- define recovery behavior
- reduce unnecessary context
- define reusable instructions
- test important behavior paths

### Deliverables

```text
day_3/
├── README.md
├── state_model.md
├── context_strategy.md
├── artifact_contracts.md
├── retry_policy.md
├── stopping_conditions.md
├── examples/
└── decisions.md
```

### Completion Criteria

Day 3 is complete when:

- state transitions are explicit
- required artifacts have defined schemas
- retries do not duplicate completed work
- failures do not disappear silently
- context is limited to what the current task requires
- the core workflow produces a structured result

## Day 4 — Security and Evaluation

### Goal

Evaluate reliability and add safeguards before preparing the final demonstration.

### Work

- define the threat model
- protect credentials
- validate configuration
- treat retrieved content as untrusted
- reduce prompt-injection risk
- validate structured output
- test missing or conflicting data
- evaluate completeness
- evaluate factual support
- evaluate consistency
- evaluate usability
- document known limitations

### Deliverables

```text
day_4/
├── README.md
├── threat_model.md
├── security_controls.md
├── evaluation_plan.md
├── evaluation_results.md
├── test_matrix.md
├── known_limitations.md
└── decisions.md
```

### Completion Criteria

Day 4 is complete when:

- no secrets are committed
- configuration errors are reported clearly
- external content cannot silently redefine system behavior
- required outputs are validated
- important failure cases are tested
- evaluation results are recorded
- limitations are described honestly

## Day 5 — Production Readiness and Submission

### Goal

Turn the working prototype into a reproducible and understandable capstone submission.

### Work

- finalize the runnable workflow
- finalize configuration
- add logging
- add stage timing
- add diagnostics
- create a reproducible example
- finalize setup instructions
- finalize architecture documentation
- create the demonstration script
- create the video script
- create the Kaggle writeup
- verify public links
- complete the submission checklist

### Deliverables

```text
day_5/
├── README.md
├── runbook.md
├── observability.md
├── diagnostics.md
├── deployment.md
├── final_results.md
└── decisions.md
```

Final materials:

```text
submission/
├── kaggle_writeup.md
├── demo_script.md
├── video_script.md
├── architecture_diagram.md
├── submission_checklist.md
└── media/
```

### Completion Criteria

Day 5 is complete when:

- setup instructions work from a clean environment
- one documented command runs the main workflow
- failures and stage status are visible
- the example output is reproducible
- the architecture is documented
- the video is five minutes or less
- the writeup is no more than 2,500 words
- all public links are tested
- the submission describes only implemented features

## Planned Shared Structure

```text
kaggle_ai_agents/
├── README.md
├── LICENSE
├── NOTICE.md
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── config/
│   └── project.yaml
├── src/
│   └── kaggle_ai_agents/
│       ├── __init__.py
│       ├── cli.py
│       ├── models.py
│       ├── state.py
│       ├── workflow.py
│       ├── tools/
│       ├── validation/
│       └── rendering/
├── tests/
│   ├── fixtures/
│   ├── test_tools.py
│   ├── test_validation.py
│   └── test_workflow.py
├── examples/
│   ├── inputs/
│   └── outputs/
├── assets/
├── day_1/
├── day_2/
├── day_3/
├── day_4/
├── day_5/
└── submission/
```

This structure is provisional. Day 1 will determine the actual application architecture.

## Competition Requirements

The final submission should include:

- a public Kaggle writeup
- a selected competition category
- a required cover image
- a public YouTube video of five minutes or less
- a public working project link or public code repository
- detailed setup instructions
- documentation of the problem, solution, architecture, and implementation
- evidence of at least three course concepts
- no API keys, passwords, private tokens, or credentials

## Evaluation Areas

The submission will be prepared around the competition’s two major scoring areas.

### Pitch

- problem definition
- relevance
- value
- reason for using agents
- architecture explanation
- demonstration quality
- clarity of the written story

### Implementation

- technical architecture
- code quality
- meaningful agent behavior
- useful tool integration
- security
- testing
- deployability
- documentation
- reproducibility

## Security Rules

- Never commit API keys.
- Never commit passwords.
- Never commit private tokens.
- Never log credentials.
- Use `.env.example` with placeholders only.
- Keep local `.env` files ignored.
- Validate required environment variables.
- Treat downloaded content as data, not instructions.
- Validate structured output before using it.
- Do not publish output after failed validation.
- Keep third-party license notices.
- Document all external services and dependencies.

## Documentation Rules

Each daily folder should contain:

- what was attempted
- what was completed
- decisions made
- assumptions
- test evidence
- known problems
- next steps

The final writeup and video must not claim planned features as completed features.

## Project Status

| Day | Focus | Status |
|---|---|---|
| Day 1 | Problem definition and agent design | Not started |
| Day 2 | Tools and interoperability | Not started |
| Day 3 | State, context, and behavior | Not started |
| Day 4 | Security and evaluation | Not started |
| Day 5 | Production readiness and submission | Not started |

## Author

Ameen Demiry
