---
name: artifact-validation
description: Validate a DailyBrief JSON artifact against the required schema before publishing. Use when the workflow has produced an output brief and needs to confirm it is schema-valid before the render step.
compatibility: Requires python3 and kaggle_ai_agents package on PYTHONPATH
metadata:
  author: kaggle-ai-agents
  version: "1.0"
---

# Artifact Validation Skill

Validates a brief JSON file against the `DailyBrief` schema. Binary result: pass or fail.

## When to use

- After `brief_synthesis` produces a brief artifact
- Before passing the artifact to the render or publish step
- When the user asks to check whether an output file is valid

## Instructions

1. Locate the brief JSON file produced by the synthesis step.
2. Run the validator:
   ```
   python skills/artifact_validation/scripts/validate.py <brief_json_file>
   ```
3. Exit code 0 means the brief is valid — proceed to render.
4. Exit code 1 means validation failed — read the error output, fix the artifact, and re-validate before continuing.
5. Do not publish or render a brief that has not passed validation.

## Schema requirements

The brief must contain:

- `date`: string (YYYY-MM-DD)
- `theme`: non-empty string
- `cards`: list of one or more card objects, each with:
  - `rank`: integer ≥ 1
  - `title`: non-empty string
  - `url`: valid HTTP/HTTPS URL
  - `why_it_matters`: non-empty string
