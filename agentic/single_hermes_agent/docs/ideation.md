# Single-Agent Ideation

This note records the archive-era direction for a smaller, skills-driven agent
runtime.

## Current Read

The single-agent track treats `agentic/single_hermes_agent/` as a design stub,
not a finished runtime. The important constraints are:

1. `llm_pipeline/` remains the deterministic baseline.
2. `agentic/hermes/` remains the multi-agent reference.
3. `agentic/kaggle_ai_agents/` remains the standalone course sandbox.
4. Shared helpers belong in `lib/` only when they are deterministic and reusable.

## What Matters

1. Skills should load on demand, not all at once.
2. Grounding and validation stay deterministic.
3. Published website artifacts stay under `app/`.

## Status

This is an ideation note only. Do not treat it as an implementation contract.
