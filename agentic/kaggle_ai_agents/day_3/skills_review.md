# Day 3 Skills Review List

This is the consolidated skills list to review before implementation hardening.

## Skills You Planned

1. source_discovery
- Purpose: find candidate items from RSS, pages, and video metadata.
- Day 2 status: partially implemented via deterministic source adapters.
- Evidence: `src/kaggle_ai_agents/tools/news_sources.py`

2. source_normalization
- Purpose: map heterogeneous inputs into one schema.
- Day 2 status: implemented for stub records.
- Evidence: `src/kaggle_ai_agents/tools/news_sources.py`

3. dedupe_and_rank
- Purpose: collapse duplicates and prioritize strong candidates.
- Day 2 status: implemented with deterministic dedupe/score/rank rules.
- Evidence: `src/kaggle_ai_agents/tools/selection.py`

4. brief_synthesis
- Purpose: produce concise why-it-matters cards.
- Day 3 status: implemented in workflow card construction.
- Evidence: `src/kaggle_ai_agents/workflow.py`

5. artifact_validation
- Purpose: enforce output schema before publish.
- Day 3 status: basic schema validator is present.
- Evidence: `src/kaggle_ai_agents/validation/schemas.py`

6. baseline_eval
- Purpose: compare against llm_pipeline baseline metrics.
- Day 3 status: implemented as parity-gap helper module with pass/fail thresholds.
- Evidence: `src/kaggle_ai_agents/tools/baseline_eval.py`, `tests/test_baseline_eval.py`

## Review Checklist

- [ ] Keep these six skill names as final labels
- [ ] Mark each skill as prototype-only or production-ready
- [ ] Decide first two skills to harden next
