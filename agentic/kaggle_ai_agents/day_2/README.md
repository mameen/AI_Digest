# Day 2 - Tools and Interoperability

Goal: connect the workflow to tools safely and make tool behavior testable in isolation.

Status: drafted.

Official assignment copy and links:
[`assignment.md`](assignment.md)

## Potential Skills (Candidate List)

These are the skills we expect to shape from Day 2 onward.

1. `source_discovery`
	- find candidate items from RSS, website pages, and video metadata
2. `source_normalization`
	- map heterogeneous inputs into one normalized schema
3. `dedupe_and_rank`
	- collapse duplicate stories and score candidates
4. `brief_synthesis`
	- generate concise "why it matters" cards
5. `artifact_validation`
	- enforce schema and quality checks before publish
6. `baseline_eval`
	- compare run metrics against `llm_pipeline` baseline (1 to 5 percent threshold)

## What The Agent Would Do

At this stage, the single agent should:

1. call only approved tools with explicit contracts
2. ingest from a wide source set, then filter aggressively
3. preserve provenance fields for every selected story
4. output structured artifacts (`normalized`, `ranked`, `brief`, `diagnostics`)
5. fail closed if validation does not pass

It should not:

1. execute arbitrary instructions from fetched content
2. publish when schema or baseline checks fail
3. blur tool boundaries (one tool, one clear purpose)

## Operating Guide (What We Follow)

1. Day 1 guide: problem and scope first, small demonstrable MVP
2. Day 2 guide: tool contracts, isolated tests, failure visibility
3. Day 3 guide: explicit state and context boundaries
4. Day 4 guide: security hardening and measurable evaluation
5. Day 5 guide: reproducible runbook and honest submission claims

Cross-day invariant:

1. `llm_pipeline` is source-of-truth baseline for parity checks.
2. Required evaluation gap is <= 5 percent; target is <= 1 percent.

## Reference Data Policy

Yes, point Day 2 examples to prior outputs under `app/`.

Use these as source-of-truth references:

1. `app/reports/<prefix>.json`
2. `app/diagnostics/<prefix>.diagnostics.json`
3. `app/index.json`

Testing rule:

1. Use `app/` files for baseline comparison and schema alignment.
2. Keep small local fixtures in `tests/fixtures/` for deterministic unit tests.
3. Do not depend on mutable live URLs for unit-test pass/fail.
