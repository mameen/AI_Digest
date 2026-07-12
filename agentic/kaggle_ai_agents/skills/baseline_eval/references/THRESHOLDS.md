# Evaluation Thresholds

## Required threshold

All tracked metrics must be within **5%** of the `llm_pipeline` baseline.
A brief that exceeds this on any metric must not be published.

## Target threshold

Aim for **1%** or less on all metrics. This is the quality bar for a strong run.

## Tracked metrics

| Metric | Source field | Notes |
|---|---|---|
| `story_count` | `brief.cards` length | Number of selected story cards |
| `avg_significance` | Fixed at 3.0 until scoring is wired | Will improve when significance scores are implemented |

## Baseline source

Loaded from `app/index.json` in the repo root.
The `latest` prefix is used by default unless `--prefix` is specified.

## Gap formula

```
gap_pct = abs(actual - baseline) / abs(baseline) * 100
```

A run passes the required threshold when the worst gap across all metrics is ≤ 5%.
