# Evaluation Results

Real evaluation metrics from running the end-to-end PoC workflow with source discovery and skills integration.

## Run 1: July 12, 2026 (Stub data)

| Date | Status | Cards | Valid | Baseline Gap | Threshold |
|---|---|---|---|---|---|
| 2026-07-12 | ✅ SUCCESS | 5 | ✅ | 94.7% | ⚠️ EXCEEDS |

### Metrics

- **Generated Brief:** 5 cards (rank, title, url, why_it_matters)
- **Validation:** ✅ DailyBrief schema valid (date, theme, cards with constraints)
- **Baseline Comparison:** Generated against app/index.json (latest report, 95 stories, 3.9 avg significance)
  - **Story Count Gap:** 94.7% (generated 5 vs baseline 95)
  - **Avg Significance Gap:** 23.1% (generated 3.0 vs baseline 3.9)
  - **Worst Gap:** 94.7% — exceeds required threshold (5%)
  - **Baseline Run:** 20260709051615 (2026-07-09)

### Interpretation

This run used **stub data** (fetch_contract_stub_items) to test the full workflow quickly. The large gap is expected because:
- Stub data intentionally provides 5 synthetic news items for testing
- Baseline report includes 95 real stories from live sources
- Significance scoring differs (stub = 3.0, baseline = 3.9)

**Next step:** Run with real sources (discover_items) to fetch from actual RSS, YouTube, and API sources. This will populate the gap with real data.

## Planned Runs

| Description | Date | Expected Gap |
|---|---|---|
| Real sources (RSS feeds) | TBD | < 5% (target) |
| Real sources + extended time | TBD | < 1% (aspirational) |

## Quality Gate

- **Required Threshold:** ≤ 5% gap (must pass to merge)
- **Target Threshold:** ≤ 1% gap (aspirational)
- **Current Status:** 🔴 FAILING (94.7% > 5%)
- **Reason:** Using stub data; will improve with real sources

---

**Evaluated by:** source_discovery + rank + validate skills  
**Evaluation Script:** `agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py`  
**Baseline Source:** `app/index.json` (LLM Pipeline reports)
