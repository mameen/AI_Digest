import json
from pathlib import Path

from kaggle_ai_agents.models import BriefCard, DailyBrief
from kaggle_ai_agents.tools.baseline_eval import (
    brief_metrics,
    evaluate_brief_against_index,
    evaluate_metric_gaps,
    load_baseline_metrics,
)


def _write_index(path: Path) -> None:
    payload = {
        "latest": "p1",
        "digests": [
            {
                "prefix": "p1",
                "story_count": 10,
                "avg_significance": 3.0,
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_baseline_metrics_from_index() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        index_path = Path(tmp) / "index.json"
        _write_index(index_path)
        prefix, metrics = load_baseline_metrics(index_path)
        assert prefix == "p1"
        assert metrics["story_count"] == 10.0
        assert metrics["avg_significance"] == 3.0


def test_evaluate_metric_gaps_pass_and_fail() -> None:
    passing = evaluate_metric_gaps(
        current_metrics={"story_count": 10.0},
        baseline_metrics={"story_count": 10.0},
    )
    assert passing["required_pass"] is True

    failing = evaluate_metric_gaps(
        current_metrics={"story_count": 1.0},
        baseline_metrics={"story_count": 10.0},
    )
    assert failing["required_pass"] is False


def test_evaluate_brief_against_index_end_to_end() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        index_path = Path(tmp) / "index.json"
        _write_index(index_path)

        brief = DailyBrief(
            date="2026-07-11",
            theme="AI signal",
            cards=[
                BriefCard(
                    rank=i + 1,
                    title=f"Item {i + 1}",
                    url=f"https://example.com/{i + 1}",
                    why_it_matters="Important",
                )
                for i in range(10)
            ],
        )

        metrics = brief_metrics(brief)
        assert metrics["story_count"] == 10.0

        result = evaluate_brief_against_index(brief=brief, index_path=index_path)
        assert result["baseline_prefix"] == "p1"
        assert result["required_pass"] is True
