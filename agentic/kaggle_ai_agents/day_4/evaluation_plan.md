# Evaluation Plan

## Baseline

Use `llm_pipeline` as the source-of-truth baseline for the same date window and source set.

Reference inputs:

1. `app/reports/<prefix>.json` for report-level metrics
2. `app/index.json` for digest summary metrics
3. `app/deploy_manifest.json` to confirm which prefix was deployed

## Metrics

1. relevance: useful stories per run
2. trust: cards with valid source links
3. novelty: duplicate-free top cards
4. brevity: digest readable in under 10 minutes
5. baseline_gap_pct: absolute percent difference versus `llm_pipeline` on agreed metrics

## Method

- run fixed fixture set
- run live sample set
- manually label top 12 cards for relevance
- compute metric deltas against `llm_pipeline` output for each run
- compare against the same `prefix` found in `app/index.json`/`app/deploy_manifest.json`

## Acceptance Threshold

1. Required: each tracked metric must be no more than 5 percent off the `llm_pipeline` baseline.
2. Target: metrics should be within 1 percent when feasible.
