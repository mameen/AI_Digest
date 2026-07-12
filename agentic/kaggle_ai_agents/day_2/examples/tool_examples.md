# Tool Examples

## rss_fetch_tool request

- source_id: openai-blog
- source_url: https://openai.com/news/rss.xml

## rss_fetch_tool response

- status: ok
- items_count: 12
- errors: []

## Baseline Reference Inputs (from app)

Use prior production-like outputs for contract checks:

1. `app/index.json`
2. `app/reports/20260709051615.json`
3. `app/diagnostics/20260709051615.diagnostics.json`

## How to Use These References

1. Validate that normalized and ranked artifacts can map to report fields used in `app/reports/*.json`.
2. Validate that run-level diagnostics can map to `app/diagnostics/*.diagnostics.json` fields.
3. Compare selected metric deltas against the same prefix baseline for the 1 to 5 percent threshold.
