# pipeline compatibility layer

This folder is a temporary compatibility package.

- Purpose: keep legacy import paths (`pipeline.*`) working while code migrates to `llm_pipeline.*`.
- Policy: do not add new logic here.
- Policy: do not add new imports from `pipeline.*` in runtime code, tests, or docs.

## Safe removal checklist

1. Runtime imports
- Confirm no runtime module imports `pipeline.*`.
- Confirm all entry points import `llm_pipeline.*` directly.

2. Tests
- Confirm test files import `llm_pipeline.*`.
- Run `python run_tests.py` and ensure green.

3. Docs and scripts
- Replace command snippets that reference `pipeline.*` with `llm_pipeline.*`.
- Verify onboarding docs and tuning docs are updated.

4. Repo scan gate
- `grep -RIn -E "from pipeline\\.|import pipeline\\." .`
- Expected result before removal: no hits outside `pipeline/` itself.

5. Removal step
- Delete `pipeline/` in one dedicated commit.
- Re-run full tests and smoke-run key commands.

## Notes

- If a legacy external script still depends on `pipeline.*`, keep a minimal shim window and document the dependency explicitly.
