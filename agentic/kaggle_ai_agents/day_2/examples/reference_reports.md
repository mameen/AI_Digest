# Reference Reports (Day 2)

This folder points to canonical reference artifacts under `app/` using relative paths.

## Recommended Baseline Prefixes

1. 20260709051615
2. 20260708120000
3. 20260707182407

## Paths

1. `../../../../app/index.json`
2. `../../../../app/reports/<prefix>.json`
3. `../../../../app/diagnostics/<prefix>.diagnostics.json`

## Why

- They provide realistic, stable schemas.
- They align the Kaggle workflow with existing production-like outputs.
- They support objective parity checks against `llm_pipeline`-derived results.
