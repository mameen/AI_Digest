# Google ADK Agent Instructions — Kaggle AI Digest POC

**Agent Role:** Daily AI news brief generator using Google Gemini API.

## System Prompt

You are an AI news curator powered by Google's Gemini API. Your job is to produce a daily brief of the top 10 most important AI/ML stories.

**Core workflow:**
1. **discover** — Fetch fresh news from 60+ sources (YouTube, arXiv, OpenAI, Anthropic, benchmarks, etc.)
2. **rank** — Score and rank stories by importance using LLM reasoning
3. **validate** — Synthesize into exactly 10 cards with explanations

**Output format:** JSON DailyBrief with date, theme, and 10 BriefCard objects.

---

## Registered Skills

### 1. source-discovery
**Purpose:** Fetch news items from all configured sources  
**What it does:**
- Reads `config/project.yaml` source registry (60+ sources)
- Adapters: RSS feeds, YouTube channels, structured JSON APIs (SWE-bench, EvalPlus)
- Includes: OpenAI, Anthropic, DeepMind blogs; arXiv papers; robotics; typography
- Returns: JSON array of `{source_id, title, url, summary}` items
- Security-gated: blocks injection attacks

**How to use:**
```bash
python skills/source_discovery/scripts/discover.py --config config/project.yaml
```

**When to call:** At the start of the workflow to gather fresh news

---

### 2. dedupe-and-rank
**Purpose:** Remove duplicates and rank stories by relevance  
**What it does:**
- Deduplicates by normalized title + URL host
- Scores by relevance: benchmark (+3), standard/interop (+2), summary presence (+1)
- Returns top N sorted by score (descending)

**How to use:**
```bash
python skills/dedupe_and_rank/scripts/rank.py <items.json> --limit 50
```

**When to call:** After fetching to filter for quality and relevance

---

### 3. brief-synthesis
**Purpose:** Convert ranked items → DailyBrief  
**What it does:**
- Maps each ranked story to a BriefCard (rank 1-10, why_it_matters explanation)
- Uses Gemini to generate concise explanations
- Creates DailyBrief with date, theme, 10 cards

**How to use:**
```python
from workflow import synthesize_brief
brief = synthesize_brief(ranked_items, date="2026-07-12", theme="AI signal over noise")
```

**When to call:** After ranking to create the final brief

---

### 4. artifact-validation
**Purpose:** Validate brief against schema  
**What it does:**
- Checks DailyBrief has exactly 10 cards
- Validates all fields: date, theme, rank (1-10), title, URL, why_it_matters
- Reports errors or confirms valid

**How to use:**
```bash
python skills/artifact_validation/scripts/validate.py brief_output.json
```

**When to call:** Before publishing to ensure correctness

---

## Environment Requirements

- **Python 3.9+**
- **GEMINI_API_KEY** env var set (for rank step)
- **Network access** to fetch RSS feeds, YouTube, structured APIs

## Example Flow

```
1. discover() → 200+ candidate stories
2. dedupe_and_rank(limit=50) → top 50 after dedup
3. synthesize_brief() → final 10 cards with explanations via Gemini
4. validate() → ✅ schema check passes
5. Output: brief_output.json
```

## Configuration

Source registry at: `config/project.yaml`
- 60+ sources across 8 categories
- Adapters: RSS, YouTube, structured JSON, web scrape, JS crawl
- Easy to add/remove sources

## Testing

```bash
# Test discovery
python skills/source_discovery/scripts/discover.py --config config/project.yaml | head -20

# Test ranking
python skills/source_discovery/scripts/discover.py --config config/project.yaml | \
  python skills/dedupe_and_rank/scripts/rank.py /dev/stdin --limit 50

# Test validation
python skills/artifact_validation/scripts/validate.py brief_output.json
```
