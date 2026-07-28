# SKILL Store

Central registry of all skills in the AI Digest PoC. Each skill is a reusable, testable, documented component that solves a specific step in the daily brief workflow.

## Quick Reference Table

| Skill | Level | Instructions | Script | Resources | References | Status |
|---|---|---|---|---|---|---|
| **source-discovery** | 4 | [SKILL.md](agentic/kaggle_ai_agents/skills/source_discovery/SKILL.md) | [discover.py](agentic/kaggle_ai_agents/skills/source_discovery/scripts/discover.py) | — | [adapter roadmap](#adapters) | ✅ Complete |
| **dedupe-and-rank** | 4 | [SKILL.md](agentic/kaggle_ai_agents/skills/dedupe_and_rank/SKILL.md) | [rank.py](agentic/kaggle_ai_agents/skills/dedupe_and_rank/scripts/rank.py) | — | [scoring rules](#scoring) | ✅ Complete |
| **artifact-validation** | 4 | [SKILL.md](agentic/kaggle_ai_agents/skills/artifact_validation/SKILL.md) | [validate.py](agentic/kaggle_ai_agents/skills/artifact_validation/scripts/validate.py) | — | [schema ref](#schema) | ✅ Complete |
| **baseline-eval** | 4 | [SKILL.md](agentic/kaggle_ai_agents/skills/baseline_eval/SKILL.md) | [evaluate.py](agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py) | [THRESHOLDS.md](agentic/kaggle_ai_agents/skills/baseline_eval/references/THRESHOLDS.md) | [quality gate](#references) | ✅ Complete |
| **source-normalization** | 1 | [SKILL.md](agentic/kaggle_ai_agents/skills/source_normalization/SKILL.md) | — | — | — | 📋 Stub |

---

## Skill Descriptions

### 1. source-discovery (Level 4)

**Purpose:** Fetch news items from configured sources and apply security filtering.

**Location:** [`agentic/kaggle_ai_agents/skills/source_discovery/`](agentic/kaggle_ai_agents/skills/source_discovery/)

**When to use:**
- At the start of the workflow to gather fresh items
- When adding a new source to the registry
- When the user asks to "collect news from all sources"

**Instructions:** [SKILL.md](agentic/kaggle_ai_agents/skills/source_discovery/SKILL.md)
- Load source registry from `config/project.yaml`
- Fetch items from RSS and other adapters
- Apply security gate filtering to block injection attacks
- Output JSON array of clean items

**Script:** [`scripts/discover.py`](agentic/kaggle_ai_agents/skills/source_discovery/scripts/discover.py)
```bash
python skills/source_discovery/scripts/discover.py --config config/project.yaml [--sources source_id ...]
```
- Exit 0: success, JSON array to stdout
- Exit 1: error (check stderr)

**Data Flow:**
- Input: `config/project.yaml` source registry
- Process: iterate sources → call adapters (rss_fetcher, youtube_channel, etc.) → security_gate.filter_items()
- Output: JSON with `{source_id, title, url, summary}` objects

**Adapters:**
| Kind | Implementation | Status |
|---|---|---|
| `rss` | urllib + xml.etree (tools.rss_fetcher) | ✅ |
| `youtube_rss` | urllib + xml.etree (tools.rss_fetcher) | ✅ |
| `youtube_channel` | (stub) | 🔄 TODO |
| `web_scrape` | (stub) | 🔄 TODO |
| `js_crawl` | (stub) | 🔄 TODO |
| `structured_json` | (stub) | 🔄 TODO |
| `mixed` | (stub) | 🔄 TODO |

**Tests:** [`tests/test_source_discovery.py`](tests/test_source_discovery.py) (8 tests)
- Config loading and filtering
- JSON schema validation
- Security gate integration
- Error handling

**Dependencies:**
- `tools.rss_fetcher` — parse RSS 2.0 and Atom feeds
- `tools.security_gate` — deny-list filter for injection attacks
- `models.NewsItem` — pydantic model for items
- `tools.news_sources` — source registry loader

---

### 2. dedupe-and-rank (Level 4)

**Purpose:** Remove duplicate news items and rank survivors by relevance.

**Location:** [`agentic/kaggle_ai_agents/skills/dedupe_and_rank/`](agentic/kaggle_ai_agents/skills/dedupe_and_rank/)

**When to use:**
- After fetching items from multiple sources that may overlap
- Before passing items to the brief synthesis step
- To produce a shortlist of the most relevant stories

**Instructions:** [SKILL.md](agentic/kaggle_ai_agents/skills/dedupe_and_rank/SKILL.md)
- Collect fetched `NewsItem` records as JSON array
- Deduplicate by normalized title + URL host
- Score by relevance signals (benchmark, standard, interoperability, summary presence)
- Rank by score descending, then alphabetically by title

**Script:** [`scripts/rank.py`](agentic/kaggle_ai_agents/skills/dedupe_and_rank/scripts/rank.py)
```bash
python skills/dedupe_and_rank/scripts/rank.py <items_json_file> [--limit N]
```
- Input: JSON array of `{source_id, title, url, summary}` objects
- Output: ranked, deduplicated JSON array
- Exit 0: success, 1: error

**Scoring:**
- +3 if title/summary contains "benchmark"
- +2 if title/summary contains "standard" or "interoperability"
- +1 if non-empty summary present
- Ties sorted alphabetically by title

**Tests:** Covered in [`tests/test_tools.py`](tests/test_tools.py)
- Deduplication by title+host
- Scoring logic
- Limit parameter

**Dependencies:**
- `tools.selection.rank_items()` — ranking algorithm
- `models.NewsItem` — pydantic model

---

### 3. artifact-validation (Level 4)

**Purpose:** Validate that a generated brief matches the required schema.

**Location:** [`agentic/kaggle_ai_agents/skills/artifact_validation/`](agentic/kaggle_ai_agents/skills/artifact_validation/)

**When to use:**
- Before publishing a brief to verify correctness
- During development to catch schema mismatches
- In CI/CD to gate merges

**Instructions:** [SKILL.md](agentic/kaggle_ai_agents/skills/artifact_validation/SKILL.md)
- Load brief JSON from file
- Validate against DailyBrief schema (date, theme, cards)
- Each card must have: rank, title, url, why_it_matters
- Report errors or confirm valid

**Script:** [`scripts/validate.py`](agentic/kaggle_ai_agents/skills/artifact_validation/scripts/validate.py)
```bash
python skills/artifact_validation/scripts/validate.py <brief_json_file>
```
- Exit 0: valid schema
- Exit 1: schema violations (error message to stderr)

**Schema:** Pydantic `DailyBrief` model
```python
DailyBrief:
  - date: str (YYYY-MM-DD)
  - theme: str
  - cards: list[BriefCard]
    - rank: int (≥ 1)
    - title: str
    - url: HttpUrl (valid http/https)
    - why_it_matters: str
```

**Tests:** Covered in [`tests/test_tools.py`](tests/test_tools.py)
- Valid brief passes
- Missing fields fail
- Invalid rank fails
- Invalid URL fails

**Dependencies:**
- `models.DailyBrief`, `models.BriefCard` — pydantic schemas

---

### 4. baseline-eval (Level 4)

**Purpose:** Compare a generated brief against a baseline (app/index.json) to detect regressions.

**Location:** [`agentic/kaggle_ai_agents/skills/baseline_eval/`](agentic/kaggle_ai_agents/skills/baseline_eval/)

**When to use:**
- After regenerating the brief to ensure quality hasn't degraded
- To measure improvements or track drift
- To gate CI/CD merges with quality thresholds

**Instructions:** [SKILL.md](agentic/kaggle_ai_agents/skills/baseline_eval/SKILL.md)
- Load generated brief and baseline brief
- Compare card-by-card (title similarity, URL match, presence)
- Measure gap as percentage of mismatches
- Reject if gap exceeds required threshold (≤5%) or warn if above target (≤1%)

**Script:** [`scripts/evaluate.py`](agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py)
```bash
python skills/baseline_eval/scripts/evaluate.py <generated_brief.json> [--baseline baseline.json]
```
- Exit 0: gap ≤ 5% (within required threshold)
- Exit 1: gap > 5% (exceeds required threshold)

**References:** [`references/THRESHOLDS.md`](agentic/kaggle_ai_agents/skills/baseline_eval/references/THRESHOLDS.md)
- **Required threshold:** ≤ 5% gap (must pass to merge)
- **Target threshold:** ≤ 1% gap (aspirational)
- **Gap definition:** percentage of baseline cards not found in generated brief (ignoring rank order)

**Tests:** Covered in [`tests/test_tools.py`](tests/test_tools.py)
- Within required threshold: exit 0
- Exceeds required threshold: exit 1
- Baseline loaded from default path

**Dependencies:**
- `models.DailyBrief` — schema validation
- Baseline brief at `app/index.json` (committed fixture)

---

### 5. source-normalization (Level 1)

**Purpose:** Describe field mapping rules for heterogeneous source data.

**Location:** [`agentic/kaggle_ai_agents/skills/source_normalization/`](agentic/kaggle_ai_agents/skills/source_normalization/)

**When to use:**
- As reference documentation when implementing new source adapters
- To understand the shared `NewsItem` schema
- When debugging mismatches between raw source data and normalized output

**Instructions:** [SKILL.md](agentic/kaggle_ai_agents/skills/source_normalization/SKILL.md)
- Different sources have different field names (headline vs. title, excerpt vs. summary, etc.)
- Always map to the shared `NewsItem` schema:
  - `source_id`: source identifier from registry
  - `title`: headline/name/title field
  - `url`: link/source_url/url field
  - `summary`: description/excerpt/body field (capped at 500 chars)

**Data Mapping Guide:**
| Source Kind | Raw Fields | → NewsItem |
|---|---|---|
| RSS | title, link, description, content:encoded | → title, url, summary |
| YouTube | title, video_id, description | → title, url, summary |
| Web scrape | headline, page_url, article_body | → title, url, summary |
| JSON API | name, source_url, excerpt | → title, url, summary |

**Tests:** Covered in [`tests/test_tools.py`](tests/test_tools.py)
- `tools.news_sources.normalize_source_records()` tested

**Dependencies:**
- `models.NewsItem` — target schema
- Source adapters implement this mapping

---

## Skill Lifecycle

### Phase 1: Design (Instruction)
- Write SKILL.md with usage and concepts
- No scripts yet
- Example: source_normalization

### Phase 2: Prototype (Script)
- Add `scripts/` with a CLI tool
- Scripts are deterministic, testable, independent
- Can be called from agent or workflow
- Example: dedupe_and_rank, artifact_validation

### Phase 3: Integration (Workflow)
- Wire into `run_daily_brief()` orchestration
- Chain skills: discover → dedupe → validate → eval
- TBD: not yet implemented

### Phase 4: Observability (Monitoring)
- Add metrics/tracing to understand performance
- TBD: future enhancement

---

## Testing Strategy

**TDD discipline:** Write failing tests first, implement to pass.

**Test files:**
- `tests/test_source_discovery.py` — 8 tests for discover.py
- `tests/test_tools.py` — 6 tests for shared tools (ranking, validation, baseline)
- `tests/test_skills.py` — 9 tests for SKILL.md structure across all skills

**Fixture-backed:** Real data, no mocks
- RSS fixtures in `tests/fixtures/rss/` (synthetic XML, no PII)
- Baseline brief in `app/index.json` (committed golden copy)

**Coverage:**
- Happy path (valid input → correct output)
- Error paths (missing file, invalid schema, etc.)
- Integration (security gate with rss_fetcher, etc.)

---

## Running Skills

### Single skill
```bash
# Discover items
python agentic/kaggle_ai_agents/skills/source_discovery/scripts/discover.py --config agentic/kaggle_ai_agents/config/project.yaml --sources openai-blog

# Rank items (from discover.py output saved to file)
python agentic/kaggle_ai_agents/skills/dedupe_and_rank/scripts/rank.py items.json --limit 10

# Validate brief
python agentic/kaggle_ai_agents/skills/artifact_validation/scripts/validate.py brief.json

# Evaluate against baseline
python agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py brief.json
```

### Full test suite
```bash
python run_tests.py    # 274 Python + 27 Node tests
python -m pytest tests/test_source_discovery.py -v  # Just discovery
```

---

## Roadmap

### Q1 2026 (Current)
- ✅ source_discovery: Level 4, RSS support
- ✅ dedupe_and_rank: Level 4
- ✅ artifact_validation: Level 4
- ✅ baseline_eval: Level 4
- ✅ source_normalization: Level 1 (reference)

### Q2 2026 (Next)
- 🔄 Workflow integration: wire skills into run_daily_brief()
- 🔄 Additional adapters: youtube_channel, web_scrape, js_crawl, structured_json
- 🔄 Evaluation results: populate baseline_eval with real numbers

### Q3 2026 (Future)
- 📋 Observability: add tracing and metrics
- 📋 CI/CD gating: use baseline_eval to block merges
- 📋 Multi-language support: adapt skills for other languages

---

## Contributing

To add a new skill:

1. **Design phase:** Create `skills/<skill-name>/SKILL.md` (Level 1)
   - Write instructions explaining when/how to use
   - Document the concept

2. **Prototype phase:** Add `scripts/<skill-name>.py` (Level 4)
   - Write failing tests first (`tests/test_<skill-name>.py`)
   - Implement script to pass tests
   - Support `--help` and exit codes

3. **Integration phase:** Update workflow
   - Wire into `run_daily_brief()` or orchestration
   - Add integration tests
   - Update this SKILL_store.md

4. **Test & commit:**
   ```bash
   python run_tests.py  # All tests pass
   git add -A -- ':!.piiignore'
   git commit -m "Skill: <skill-name> at Level X with Y tests"
   ```

---

## Related Documentation

- [HOWTO.md](./HOWTO.md) — Quick reference for common tasks
- [day_3/skills_review.md](agentic/kaggle_ai_agents/day_3/skills_review.md) — 6-skill inventory table and SKILL.md format guide
- [day_4/quality_protection_plan.md](agentic/kaggle_ai_agents/day_4/quality_protection_plan.md) — Reflection loop mechanisms and threat models
- [README.md](./README.md) — Project overview and architecture

---

**Last updated:** 2026-07-12  
**Total skills:** 5 (4 Level 4 + 1 Level 1)  
**Total tests:** 47+ (fixture-backed, no mocks)  
**Status:** ✅ All tests passing (274 Python + 27 Node)
