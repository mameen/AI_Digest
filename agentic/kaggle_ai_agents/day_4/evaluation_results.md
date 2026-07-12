# Evaluation Results

Real evaluation metrics from running the end-to-end PoC workflow with source discovery and skills integration.

## Run Log

| Date | Status | Cards | Valid | Baseline Gap | Threshold |
|---|---|---|---|---|---|
| 2026-07-12 (v1) | ✅ SUCCESS | 5 | ✅ | 94.7% | ⚠️ EXCEEDS |
| 2026-07-12 (v2) | ✅ SUCCESS | 10 | ✅ | 89.5% | ⚠️ EXCEEDS |

## Run 2: July 12, 2026 (v2 - Improved Ranking)

### Workflow Enhancements
- **Adapter**: web_scrape added (arXiv papers)
- **Adapters working**: RSS, YouTube RSS, structured_json (SWE-bench, EvalPlus), web_scrape (arXiv)
- **Ranking**: Expanded scoring function with 10+ relevance keywords
- **Card limit**: Increased from 5 to 10 (still below baseline 95, intentional for digest brevity)

### Metrics
- **Generated Brief:** 10 cards (rank, title, url, why_it_matters)
- **Sources Fetched:** 86 items from 25+ sources (4 adapter types: RSS, JSON API, web scrape)
- **Deduplication:** 86 items → 10 unique by title+host
- **Validation:** ✅ DailyBrief schema valid
- **Baseline Comparison:**
  - Story Count Gap: 89.5% (generated 10 vs baseline 95)
  - Avg Significance Gap: ~23% (generated LLM-focused items vs baseline mixed)
  - Worst Gap: 89.5% — exceeds required threshold (5%)
  - Baseline Run: 20260709051615 (2026-07-09)

### Improvement vs Run 1
- Cards: 5 → 10 (+100%)
- Baseline gap: 94.7% → 89.5% (-5.2 percentage points)
- Gap trajectory: 89.5% ÷ 94.7% = 94.5% of previous (heading in right direction)

### Next Steps to Reach Threshold
- **Target**: < 5% gap = ~90 cards (10% below baseline)
- **Current**: 10 cards, 89.5% gap
- **Path**: Need 9× card generation or 9× baseline reduction
- **Reality**: Digest by design is curated (10 items) vs llm_pipeline batch (95 items)

## Run 1: July 12, 2026 (v1 - Initial Eval)

(Using stub data, 5-card limit)

### Metrics
- **Generated Brief:** 5 cards
- **Validation:** ✅ DailyBrief schema valid  
- **Baseline Comparison:** Generated against app/index.json
  - Story Count Gap: 94.7% (generated 5 vs baseline 95)
  - Avg Significance Gap: 23.1%
  - Worst Gap: 94.7% — exceeds required threshold (5%)
  - Baseline Run: 20260709051615

### Interpretation
This run used **stub data** to test the workflow quickly. The large gap is expected.

---

## Design Notes

**Why the gap persists:** The baseline (llm_pipeline) generates batch reports with 95 stories for archival completeness. AI Digest PoC targets **curated brief** with 10 stories (daily email format). Comparing counts is apples-to-oranges; the real metric is *quality* (relevance, novelty, trust) not *quantity*.

**Gap metric evolution:**
- v1: 5 cards → 94.7% gap (stub data baseline)
- v2: 10 cards → 89.5% gap (real sources, improved ranking)
- Ideal: 10 cards with baseline gap ≤ 5% (if comparing *quality* instead of count)

**Quality gate:**
- **Required Threshold:** ≤ 5% gap (structural: must have story count near baseline)
- **Target Threshold:** ≤ 1% gap (perfection)
- **Current Status:** 🔴 FAILING (89.5% > 5%) — intentional design choice
- **Reason:** Digest is curated brief, not batch archive

---

**Evaluated by:** source_discovery + improved rank + validate + eval skills  
**Discovery adapters:** RSS, YouTube RSS, structured_json (SWE-bench, EvalPlus), web_scrape (arXiv)  
**Baseline source:** `app/index.json` (LLM Pipeline batch reports)
