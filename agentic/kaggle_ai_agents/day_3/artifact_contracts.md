# Artifact Contracts

Reference shape from production app artifacts:

- `app/index.json` digest list fields (`prefix`, `date`, `summary`, `story_count`, `avg_significance`, `categories`, `report_source`)
- `app/reports/<prefix>.json` report payload
- `app/diagnostics/<prefix>.diagnostics.json` diagnostics payload

## normalized_items.json

- list of normalized source items
- required fields: `source_id`, `source_url`, `title`, `canonical_url`, `published_at`, `source_channel`

## ranked_items.json

- list sorted by deterministic score
- required fields: `score`, `score_reason`, `novelty_bucket`, `category_hint`

## daily_brief.json

- date
- prefix (timestamp-like run id)
- theme
- cards[] with rank, title, url, why_it_matters
- summary
- story_count
- avg_significance
- categories (counts by category id)
- report_source (expected: `kaggle-agent`)

## diagnostics.json

- run_id
- stage_durations_ms
- source_failures
- validation_errors
- output_paths
- baseline_compare (`llm_pipeline` deltas)
