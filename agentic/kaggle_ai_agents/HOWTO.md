# How-To Guide

Quick reference for common tasks in this project.

---

## Run the tests

```bash
PYTHONPATH=agentic/kaggle_ai_agents/src python -m pytest agentic/kaggle_ai_agents/tests -q
```

All 21 tests should pass. Run this after any code change.

---

## Run the evaluation (baseline parity check)

Generate a brief first, then evaluate it against the production baseline:

```bash
# 1. Produce a brief
PYTHONPATH=agentic/kaggle_ai_agents/src python -m kaggle_ai_agents.cli > /tmp/brief.json

# 2. Evaluate against app/index.json (uses latest prefix by default)
python agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py \
  /tmp/brief.json \
  app/index.json

# 3. Evaluate against a specific prefix
python agentic/kaggle_ai_agents/skills/baseline_eval/scripts/evaluate.py \
  /tmp/brief.json \
  app/index.json \
  --prefix 20260709051615
```

Exit 0 = within required threshold (≤5%). Exit 1 = fails — do not publish.

---

## Validate an artifact

Check whether a brief JSON file is schema-valid before publishing:

```bash
python agentic/kaggle_ai_agents/skills/artifact_validation/scripts/validate.py \
  /path/to/brief.json
```

---

## Deduplicate and rank items

Given a JSON file of raw items, produce a ranked shortlist:

```bash
python agentic/kaggle_ai_agents/skills/dedupe_and_rank/scripts/rank.py \
  /path/to/items.json \
  --limit 10
```

Input format: `[{source_id, title, url, summary}, ...]`

---

## Add a new source

1. Open `agentic/kaggle_ai_agents/config/project.yaml`.
2. Add an entry under `sources:` with the required fields:

```yaml
- id: my-new-source
  kind: rss          # rss | web_scrape | youtube_channel | js_crawl | structured_json
  label: My Source
  url: https://example.com/feed.xml
  limit: 10          # optional
```

3. Run `tests/test_tools.py` and add a spot-check assertion for the new source id in `test_load_source_registry_has_full_inventory`.

Source kinds:
- `rss` — standard RSS/Atom feed
- `web_scrape` — HTML page with no public API
- `youtube_channel` — YouTube channel with a `channel_id`
- `js_crawl` — JS-rendered page that needs a headless browser
- `structured_json` — public JSON API endpoint

---

## Add a new skill

1. Create a directory under `agentic/kaggle_ai_agents/skills/<skill-name>/`.
2. Add a `SKILL.md` with required frontmatter:

```
---
name: skill-name          # must match directory name, lowercase-hyphens
description: One sentence — what it does and when to use it.
metadata:
  author: kaggle-ai-agents
  version: "1.0"
---

# Skill Name

Instructions for the agent...
```

3. Optionally add:
   - `scripts/` — Python scripts the agent can run (exit 0 = pass, 1 = fail)
   - `references/` — reference docs loaded on demand
   - `assets/` — templates and examples

4. If the skill has scripts, add a test in `tests/test_skills.py`:

```python
def test_my_skill_script_passes() -> None:
    result = _run(SKILLS_DIR / "my-skill/scripts/run.py", tmp_input)
    assert result.returncode == 0, result.stderr
```

5. Run the full test suite to confirm `test_all_skills_have_skill_md` and `test_all_skill_md_have_required_frontmatter` pick up the new skill.

---

## Update the skills review table

After adding or changing a skill, update `day_3/skills_review.md` — specifically the **Skills Inventory** table — to reflect the new status and evidence path.

---

## Add a new test

Tests live in `agentic/kaggle_ai_agents/tests/`.

- Tool logic → `test_tools.py`
- Workflow → `test_workflow.py`
- Schema validation → `test_validation.py`
- Baseline evaluation → `test_baseline_eval.py`
- Skill structure and scripts → `test_skills.py`

Run with:
```bash
PYTHONPATH=agentic/kaggle_ai_agents/src python -m pytest agentic/kaggle_ai_agents/tests -q
```

---

## Commit changes

Always run tests before committing. Use a descriptive message with a substantive PII trailer:

```bash
git add -A && git commit \
  -m "Short description of the change" \
  -m "Bullet detail 1" \
  -m "Bullet detail 2" \
  -m "PII-Reviewed: <brief statement that no secrets or private data are present>"
```
