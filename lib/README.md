# lib/

Shared Python utilities used by the AI Digest POCs.

This package contains reusable code extracted from the original staged pipeline:
configuration, date windows, diagnostics, report rendering, source grounding,
schema validation, source parsing, and small Hermes-specific adapters.

## Structure

| Path | Purpose |
|---|---|
| [`*.py`](.) | Shared digest primitives used by pipeline and agentic experiments |
| [`hermes/`](hermes/) | Hermes-specific adapters for the multi-agent POC |
| [`ingest/`](ingest/) | Source ingestion helpers |
| [`tests/`](tests/) | Unit tests for shared library behavior |

## Rules

1. Keep `lib/` free of product presentation copy.
2. Keep runtime-specific code in a runtime-specific subpackage, such as
   `lib/hermes/`.
3. Do not import from `agentic/` or `llm_pipeline/` inside generic shared
   modules.
4. Prefer deterministic helpers here when they are useful to more than one POC.

The archive-facing POC overview lives in [`../README.md`](../README.md).
