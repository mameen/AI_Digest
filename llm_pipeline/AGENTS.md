# llm_pipeline/

Module guidance for the LLM Pipeline POC.

The archive-facing overview lives in [`../README.md`](../README.md). This folder
is the stable staged baseline for AI Digest: ingest, enrich, validate, render.

## Mandate

1. Keep the pipeline runnable from `python run.py`.
2. Keep deterministic validation and grounding behavior honest and auditable.
3. Prefer shared deterministic helpers in `../lib/` when they are reused by more
   than one POC.
4. Do not remove or rewrite pipeline behavior just to simplify the archive unless
   tests and a smoke run prove the behavior still works.

## Extraction History

Some reusable modules have already been extracted or mirrored into `../lib/`.
Historical track handoff notes were consolidated into
[`../agentic/hermes/docs/ARCHIVE_NOTES.md`](../agentic/hermes/docs/ARCHIVE_NOTES.md)
during archive cleanup.

## Refactoring Rules

1. Move code only when there is a real second consumer.
2. Preserve public APIs when moving a module.
3. Move or add tests with the code.
4. Run `python run_tests.py` after changes.
5. Treat `../app/` as the approved website payload; source report folders may
   contain development outputs.

## Tests

```powershell
python run_tests.py
```

Use fixture-backed tests where possible. Do not fabricate data to make a report
look cleaner.