# Day 1 — Introduction to Agents and Vibe Coding

Official course discussion:  
https://www.kaggle.com/competitions/5-day-ai-agents-intensive-vibecoding-course-with-google/discussion/708280

Course page:  
https://www.kaggle.com/competitions/5-day-ai-agents-intensive-vibecoding-course-with-google

## Assignment

Complete Unit 1: **Introduction to Agents and Vibe Coding**.

### Required Work

- Listen to the Unit 1 summary podcast.
- Read the whitepaper **The New SDLC with Vibe Coding**.
- Complete the codelab **Get Started with Antigravity 2.0 and IDE**.
- Complete the codelab **Build a Web Application in AI Studio and Deploy to Cloud Run**.

## What Day 1 Covers

Day 1 introduces the transition from traditional manual coding toward intent-driven development.

The main idea is that natural language can become a primary interface for software development, while developers remain responsible for architecture, constraints, evaluation, safety, and final quality.

The course distinguishes between casual vibe coding and disciplined agentic engineering.

Vibe coding focuses on describing intent and allowing AI tools to generate or modify software.

Agentic engineering adds the structure required to make that process reliable:

- clear specifications
- controlled context
- explicit constraints
- evaluation criteria
- review checkpoints
- security boundaries
- reproducible workflows

## The New SDLC

The whitepaper describes how AI agents can compress parts of the traditional software development life cycle.

Traditional development often moves through separate stages:

1. requirements
2. design
3. implementation
4. testing
5. deployment
6. maintenance

With agent-assisted development, some of these stages can happen more quickly or overlap.

However, faster generation does not remove the need for engineering discipline.

The developer’s role shifts toward designing the system that guides the agent.

This includes:

- defining the goal
- providing relevant context
- setting limits
- specifying expected outputs
- creating tests
- evaluating results
- reviewing changes
- deciding what is safe to deploy

## The Factory Model

The course introduces a factory model for agentic software development.

In this model, the developer does not manually produce every line of code.

Instead, the developer designs and operates a controlled production system for software changes.

The developer acts as an orchestrator who defines:

- what should be built
- what information the agent receives
- what tools the agent may use
- what rules the agent must follow
- how output is evaluated
- when human review is required
- what conditions block deployment

The agent performs work inside that environment.

The quality of the result depends heavily on the quality of the environment created around the agent.

## Day 1 Learning Goals

By the end of Day 1, I should be able to:

- explain the difference between a chatbot and an agent
- explain the difference between vibe coding and agentic engineering
- describe how AI changes the software development life cycle
- use natural language to guide an AI development environment
- provide useful context and constraints
- review generated code rather than accepting it automatically
- use Google AI Studio to create a small application
- understand the basic path from prototype to Cloud Run deployment

## Practical Exercises

### Exercise 1 — Antigravity 2.0 and IDE

The first codelab introduces:

- Antigravity 2.0
- the Antigravity IDE
- the Antigravity CLI
- natural-language development workflows
- project generation
- iterative prompting
- reviewing generated files and changes

### Exercise 2 — Google AI Studio and Cloud Run

The second codelab introduces:

- creating a small application in Google AI Studio
- working with an AI-assisted application workflow
- preparing the application for deployment
- deploying the application to Google Cloud Run
- producing a shareable application

## My Day 1 Project Goal

For Day 1, I will define a small agent-based application before building the full capstone.

The goal is not to complete the entire project in one day.

The goal is to establish:

- one clear user problem
- one clear outcome
- one minimum complete workflow
- one initial specification
- one small working prototype
- one repeatable evaluation method

## Day 1 Work Plan

### Step 1 — Define the Problem

Write a short problem statement that answers:

- Who is the user?
- What problem does the user have?
- Why is the current process difficult?
- What result would be valuable?
- Why is an agent appropriate?

### Step 2 — Define the Minimum Workflow

Document:

- the input
- the expected action
- any tools required
- the expected output
- the stopping condition
- failure behavior

### Step 3 — Write the Initial Specification

The initial specification should include:

- project purpose
- target user
- supported use case
- excluded use cases
- functional requirements
- nonfunctional requirements
- security requirements
- acceptance criteria

### Step 4 — Build a Small Prototype

Use the course tools to create the smallest working application that proves the main idea.

The prototype does not need to include every final feature.

### Step 5 — Review the Generated Work

Check:

- whether the implementation matches the specification
- whether unnecessary files or features were added
- whether credentials are exposed
- whether errors are handled
- whether instructions are clear
- whether the project can be run again

### Step 6 — Record Results

Document:

- what was attempted
- what worked
- what failed
- what changed
- what remains uncertain
- what should move to Day 2

## Deliverables

The Day 1 folder should contain:

```text
day_1/
├── README.md
├── problem_statement.md
├── project_spec.md
├── architecture_draft.md
├── prompt_log.md
├── prototype_notes.md
├── results.md
└── decisions.md
```

## Completion Checklist

- [ ] Listened to the Unit 1 podcast
- [ ] Read **The New SDLC with Vibe Coding**
- [ ] Completed the Antigravity 2.0 codelab
- [ ] Completed the Google AI Studio and Cloud Run codelab
- [ ] Defined the target user
- [ ] Defined the problem
- [ ] Defined the minimum complete workflow
- [ ] Created the first project specification
- [ ] Created a small prototype
- [ ] Reviewed generated code and files
- [ ] Recorded failures and limitations
- [ ] Added Day 1 decisions
- [ ] Identified the starting point for Day 2

## Notes

### Podcast Notes

Add notes here after listening to the Unit 1 podcast.

### Whitepaper Notes

Add notes here after reading **The New SDLC with Vibe Coding**.

### Antigravity Notes

Add notes here after completing the Antigravity 2.0 codelab.

### Google AI Studio Notes

Add notes here after completing the Google AI Studio and Cloud Run codelab.

## Results

### What Worked

To be completed.

### What Did Not Work

To be completed.

### What I Learned

To be completed.

### What I Will Change

To be completed.

## Day 2 Handoff

Day 2 focuses on agent tools and interoperability.

Before moving to Day 2, this folder should contain a clear problem, a small working prototype, and a documented list of tools or integrations the project will require.
