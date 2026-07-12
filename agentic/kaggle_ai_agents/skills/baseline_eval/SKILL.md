---
name: baseline-eval
description: Compare a DailyBrief against the llm_pipeline baseline metrics from app/index.json. Reports gap percentages and pass/fail for required (≤5%) and target (≤1%) thresholds. Use after producing a brief to verify it is within acceptable quality range.
compatibility: Requires python3 and kaggle_ai_agents package on PYTHONPATH
metadata:
  author: kaggle-ai-agents
  version: "1.0"
---

# Baseline Evaluation Skill

Measures how far the current brief deviates from the production `llm_pipeline` baseline.

## When to use

- After artifact validation passes
- Before the publish or render step
- When the user wants to know whether this run's quality is within threshold

## Instructions

1. Locate the validated brief JSON file.
2. Locate the baseline index file (default: `app/index.json` at repo root).
3. Run the evaluator:
   ```
   python skills/baseline_eval/scripts/evaluate.py <brief_json_file> <index_json_file>
   ```
   To use a specific baseline prefix instead of the latest:
   ```
   python skills/baseline_eval/scripts/evaluate.py <brief_json_file> <index_json_file> --prefix 20260709051615
   ```
4. Read the output JSON result.
5. If `required_pass` is `true`, proceed to publish.
6. If `required_pass` is `false`, report the failing metrics and gap percentages. Do not publish.

## Thresholds

See `references/THRESHOLDS.md` for the full threshold definitions and rationale.
