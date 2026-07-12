"""Baseline parity helpers for Day 3/4 evaluation gates."""

from __future__ import annotations

import json
from pathlib import Path

from kaggle_ai_agents.models import DailyBrief


def load_baseline_metrics(index_path: str | Path, prefix: str | None = None) -> tuple[str, dict[str, float]]:
    """Load numeric baseline metrics from app index.json digest summaries."""
    path = Path(index_path)
    payload = json.loads(path.read_text(encoding="utf-8"))

    selected_prefix = prefix or payload.get("latest")
    digests = payload.get("digests", [])

    for digest in digests:
        if digest.get("prefix") != selected_prefix:
            continue
        metrics: dict[str, float] = {}
        if isinstance(digest.get("story_count"), (int, float)):
            metrics["story_count"] = float(digest["story_count"])
        if isinstance(digest.get("avg_significance"), (int, float)):
            metrics["avg_significance"] = float(digest["avg_significance"])
        return selected_prefix, metrics

    raise ValueError(f"Baseline prefix not found in index: {selected_prefix}")


def brief_metrics(brief: DailyBrief) -> dict[str, float]:
    """Convert a DailyBrief into numeric metrics for baseline comparison."""
    card_count = len(brief.cards)
    # Placeholder score until significance scoring is introduced in later iterations.
    avg_significance = 3.0 if card_count > 0 else 0.0
    return {
        "story_count": float(card_count),
        "avg_significance": avg_significance,
    }


def _gap_pct(actual: float, baseline: float) -> float:
    if baseline == 0:
        return 0.0 if actual == 0 else 100.0
    return abs(actual - baseline) / abs(baseline) * 100.0


def evaluate_metric_gaps(
    current_metrics: dict[str, float],
    baseline_metrics: dict[str, float],
    required_threshold_pct: float = 5.0,
    target_threshold_pct: float = 1.0,
) -> dict:
    """Compute parity gaps and threshold pass/fail for shared metric keys."""
    shared = sorted(set(current_metrics).intersection(baseline_metrics))
    if not shared:
        raise ValueError("No shared metric keys to compare")

    gaps: dict[str, float] = {}
    for key in shared:
        gaps[key] = round(_gap_pct(current_metrics[key], baseline_metrics[key]), 3)

    worst_gap_pct = max(gaps.values())
    return {
        "shared_metrics": shared,
        "gaps_pct": gaps,
        "worst_gap_pct": worst_gap_pct,
        "required_threshold_pct": required_threshold_pct,
        "target_threshold_pct": target_threshold_pct,
        "required_pass": worst_gap_pct <= required_threshold_pct,
        "target_pass": worst_gap_pct <= target_threshold_pct,
    }


def evaluate_brief_against_index(
    brief: DailyBrief,
    index_path: str | Path,
    prefix: str | None = None,
    required_threshold_pct: float = 5.0,
    target_threshold_pct: float = 1.0,
) -> dict:
    """High-level helper to compare current brief metrics against app baseline."""
    baseline_prefix, baseline = load_baseline_metrics(index_path=index_path, prefix=prefix)
    current = brief_metrics(brief)
    result = evaluate_metric_gaps(
        current_metrics=current,
        baseline_metrics=baseline,
        required_threshold_pct=required_threshold_pct,
        target_threshold_pct=target_threshold_pct,
    )
    result["baseline_prefix"] = baseline_prefix
    result["current_metrics"] = current
    result["baseline_metrics"] = baseline
    return result
