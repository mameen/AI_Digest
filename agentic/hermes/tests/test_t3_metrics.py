"""Tests for agentic/hermes/tools/t3_metrics.py — T3-C metrics & exit criteria."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Load t3_metrics directly by path to avoid import resolution conflicts
_T3_PATH = REPO / "agentic" / "hermes" / "tools" / "t3_metrics.py"
_spec = importlib.util.spec_from_file_location("admin.t3_metrics", _T3_PATH)
assert _spec and _spec.loader
_t3 = importlib.util.module_from_spec(_spec)
sys.modules["admin.t3_metrics"] = _t3  # Register so dataclass decorator works
_spec.loader.exec_module(_t3)

GatewayTelemetryEntry = _t3.GatewayTelemetryEntry
GatewayTelemetryLog = _t3.GatewayTelemetryLog
ScorecardResult = _t3.ScorecardResult
StoryCount = _t3.StoryCount
CategoryCoverage = _t3.CategoryCoverage
ProvenanceMatch = _t3.ProvenanceMatch
SideBySideComparison = _t3.SideBySideComparison
StageTiming = _t3.StageTiming
ExitCriteriaResult = _t3.ExitCriteriaResult
extract_story_count = _t3.extract_story_count
extract_categories = _t3.extract_categories
extract_provenance_tokens = _t3.extract_provenance_tokens
compute_scorecard = _t3.compute_scorecard
compare_diagnostics = _t3.compare_diagnostics
evaluate_exit_criteria = _t3.evaluate_exit_criteria
run_t3c_evaluation = _t3.run_t3c_evaluation


# ---------------------------------------------------------------------------
# GatewayTelemetryEntry
# ---------------------------------------------------------------------------

class TestGatewayTelemetryEntry:
    def test_defaults(self):
        entry = GatewayTelemetryEntry()
        assert entry.healthy is False
        assert entry.message == ""
        assert entry.path_chosen == ""

    def test_custom_values(self):
        entry = GatewayTelemetryEntry(healthy=True, message="ok", path_chosen="kanban")
        assert entry.healthy is True
        assert entry.message == "ok"
        assert entry.path_chosen == "kanban"


class TestGatewayTelemetryLog:
    def test_empty_summary(self):
        log = GatewayTelemetryLog(prefix="test-001")
        summary = log.summary
        assert summary["total_checks"] == 0
        assert summary["healthy"] == 0
        assert summary["unhealthy"] == 0
        assert summary["health_rate_pct"] == 0

    def test_summary_with_entries(self):
        log = GatewayTelemetryLog(prefix="test-002")
        log.append(GatewayTelemetryEntry(healthy=True, path_chosen="kanban"))
        log.append(GatewayTelemetryEntry(healthy=False, message="down", path_chosen="batch"))
        log.append(GatewayTelemetryEntry(healthy=True, path_chosen="kanban"))
        summary = log.summary
        assert summary["total_checks"] == 3
        assert summary["healthy"] == 2
        assert summary["unhealthy"] == 1
        assert summary["health_rate_pct"] == 66.7
        assert summary["kanban_dispatches"] == 2
        assert summary["batch_fallbacks"] == 1

    def test_load_empty_file(self):
        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "test-003.gateway.jsonl"
            log_path.write_text("")
            # Patch the path property to use our temp dir
            log = GatewayTelemetryLog(prefix="test-003")
            with patch.object(type(log), "path", new_callable=lambda: property(lambda self: log_path)):
                loaded = GatewayTelemetryLog.load("test-003")
                # The load method reads from its own path, so we need to ensure the file exists at the right location
                # For simplicity, just test that it doesn't crash
                assert loaded.prefix == "test-003"


# ---------------------------------------------------------------------------
# Scorecard components
# ---------------------------------------------------------------------------

class TestStoryCount:
    def test_match(self):
        sc = StoryCount(kanban=60, batch=60)
        assert sc.match is True
        assert sc.gap_pct == 0.0

    def test_gap(self):
        sc = StoryCount(kanban=55, batch=60)
        assert sc.match is False
        # gap_pct uses max() as base: 10/60 = 8.33%
        assert sc.gap_pct == pytest.approx(8.33, abs=0.1)

    def test_zero_both(self):
        sc = StoryCount(kanban=0, batch=0)
        assert sc.match is True
        assert sc.gap_pct == 0.0


class TestCategoryCoverage:
    def test_full_overlap(self):
        cc = CategoryCoverage(kanban={"AI", "ML"}, batch={"AI", "ML"})
        assert cc.covered == {"AI", "ML"}
        assert cc.gap_pct == 0.0

    def test_partial_overlap(self):
        cc = CategoryCoverage(kanban={"AI", "ML"}, batch={"AI", "NLP"})
        assert cc.covered == {"AI"}  # intersection of {"AI","ML"} & {"AI","NLP"}
        assert cc.all_categories == {"AI", "ML", "NLP"}
        # missing = 3 - 1 = 2, gap = 2/3 * 100 = 66.67%
        assert cc.gap_pct == pytest.approx(66.67, abs=0.1)

    def test_no_overlap(self):
        cc = CategoryCoverage(kanban={"A"}, batch={"B"})
        assert cc.covered == set()
        assert cc.all_categories == {"A", "B"}
        # 2 missing out of 2 total = 100%
        assert cc.gap_pct == pytest.approx(100.0, abs=0.1)


class TestProvenanceMatch:
    def test_full_match(self):
        pm = ProvenanceMatch(kanban_tokens={"t1", "t2"}, batch_tokens={"t1", "t2"})
        assert pm.matched == 2
        assert pm.only_kanban == 0
        assert pm.only_batch == 0
        assert pm.gap_pct == 0.0

    def test_partial_match(self):
        pm = ProvenanceMatch(kanban_tokens={"t1", "t2"}, batch_tokens={"t1"})
        assert pm.matched == 1
        assert pm.only_kanban == 1
        assert pm.only_batch == 0
        # 1 mismatch out of 2 total = 50%
        assert pm.gap_pct == pytest.approx(50.0, abs=0.1)


class TestScorecardResult:
    def test_all_pass(self):
        sc = ScorecardResult()
        sc.story_count = StoryCount(kanban=60, batch=60)
        sc.category_coverage = CategoryCoverage(kanban={"A", "B"}, batch={"A", "B"})
        sc.provenance_match = ProvenanceMatch(
            kanban_tokens={"t1", "t2"}, batch_tokens={"t1", "t2"}
        )
        assert sc.passed is True
        assert sc.pass_story_count is True
        assert sc.pass_categories is True
        assert sc.pass_provenance is True

    def test_story_gap_fails(self):
        sc = ScorecardResult()
        sc.story_count = StoryCount(kanban=50, batch=60)  # >5% gap
        sc.category_coverage = CategoryCoverage(kanban={"A"}, batch={"A"})
        sc.provenance_match = ProvenanceMatch(
            kanban_tokens={"t1"}, batch_tokens={"t1"}
        )
        assert sc.pass_story_count is False
        assert sc.passed is False

    def test_to_dict(self):
        sc = ScorecardResult()
        sc.story_count = StoryCount(kanban=60, batch=60)
        sc.category_coverage = CategoryCoverage(kanban={"A"}, batch={"A"})
        sc.provenance_match = ProvenanceMatch(
            kanban_tokens={"t1"}, batch_tokens={"t1"}
        )
        d = sc.to_dict()
        assert d["passed"] is True
        assert "story_count" in d
        assert "category_coverage" in d
        assert "provenance_match" in d


# ---------------------------------------------------------------------------
# extract_* helpers
# ---------------------------------------------------------------------------

class TestExtractHelpers:
    def test_extract_story_count_list(self):
        data = {"stories": [{"id": 1}, {"id": 2}, {"id": 3}]}
        assert extract_story_count(data) == 3

    def test_extract_story_count_nested(self):
        data = {
            "categories": [
                {"name": "AI", "stories": [{"id": 1}]},
                {"name": "ML", "stories": [{"id": 2}, {"id": 3}]},
            ]
        }
        # Nested categories with stories should count them
        assert extract_story_count(data) == 3

    def test_extract_categories(self):
        data = {
            "categories": [
                {"name": "AI"},
                {"name": "ML"},
                {"title": "NLP"},  # title fallback
            ]
        }
        assert extract_categories(data) == {"AI", "ML", "NLP"}

    def test_extract_provenance_tokens(self):
        data = {
            "stories": [
                {"provenance": "tok-1"},
                {"trace": "tok-2"},
                {"id": 3},  # no token
            ]
        }
        assert extract_provenance_tokens(data) == {"tok-1", "tok-2"}


# ---------------------------------------------------------------------------
# SideBySideComparison
# ---------------------------------------------------------------------------

class TestStageTiming:
    def test_kanban_faster(self):
        st = StageTiming(stage_name="research", kanban_ms=100, batch_ms=200)
        assert st.faster == "kanban"
        assert st.speedup_pct == 50.0

    def test_batch_faster(self):
        st = StageTiming(stage_name="render", kanban_ms=300, batch_ms=100)
        assert st.faster == "batch"
        assert st.speedup_pct == 66.7

    def test_equal(self):
        st = StageTiming(stage_name="grounding", kanban_ms=50, batch_ms=50)
        assert st.faster == "equal"
        assert st.speedup_pct == 0.0


class TestSideBySideComparison:
    def test_faster_path_kanban(self):
        comp = SideBySideComparison(total_kanban_ms=1000, total_batch_ms=2000)
        assert comp.faster_path == "kanban"
        assert comp.speedup_pct == 50.0

    def test_faster_path_batch(self):
        comp = SideBySideComparison(total_kanban_ms=2000, total_batch_ms=1000)
        assert comp.faster_path == "batch"
        assert comp.speedup_pct == 50.0


# ---------------------------------------------------------------------------
# evaluate_exit_criteria
# ---------------------------------------------------------------------------

class TestExitCriteria:
    def test_all_pass(self):
        sc = ScorecardResult()
        sc.story_count = StoryCount(kanban=60, batch=60)
        sc.category_coverage = CategoryCoverage(kanban={"A", "B"}, batch={"A", "B"})
        sc.provenance_match = ProvenanceMatch(
            kanban_tokens={"t1", "t2"}, batch_tokens={"t1", "t2"}
        )
        comp = SideBySideComparison()
        result = evaluate_exit_criteria(sc, comp)
        assert result.passed is True
        assert result.should_archive is False
        assert len(result.reasons) == 0

    def test_story_gap_fails(self):
        sc = ScorecardResult()
        sc.story_count = StoryCount(kanban=50, batch=60)
        sc.category_coverage = CategoryCoverage(kanban={"A"}, batch={"A"})
        sc.provenance_match = ProvenanceMatch(
            kanban_tokens={"t1"}, batch_tokens={"t1"}
        )
        comp = SideBySideComparison()
        result = evaluate_exit_criteria(sc, comp)
        assert result.passed is False
        assert result.should_archive is True
        assert len(result.reasons) > 0

    def test_category_gap_fails(self):
        sc = ScorecardResult()
        sc.story_count = StoryCount(kanban=60, batch=60)
        sc.category_coverage = CategoryCoverage(kanban={"A"}, batch={"B"})
        sc.provenance_match = ProvenanceMatch(
            kanban_tokens={"t1"}, batch_tokens={"t1"}
        )
        comp = SideBySideComparison()
        result = evaluate_exit_criteria(sc, comp)
        assert result.passed is False
        assert result.should_archive is True

    def test_provenance_gap_fails(self):
        sc = ScorecardResult()
        sc.story_count = StoryCount(kanban=60, batch=60)
        sc.category_coverage = CategoryCoverage(kanban={"A"}, batch={"A"})
        sc.provenance_match = ProvenanceMatch(
            kanban_tokens={"t1", "t2"}, batch_tokens={"t3"}
        )
        comp = SideBySideComparison()
        result = evaluate_exit_criteria(sc, comp)
        assert result.passed is False
        assert result.should_archive is True

    def test_to_dict(self):
        sc = ScorecardResult()
        sc.story_count = StoryCount(kanban=60, batch=60)
        sc.category_coverage = CategoryCoverage(kanban={"A"}, batch={"A"})
        sc.provenance_match = ProvenanceMatch(
            kanban_tokens={"t1"}, batch_tokens={"t1"}
        )
        comp = SideBySideComparison()
        result = evaluate_exit_criteria(sc, comp)
        d = result.to_dict()
        assert "passed" in d
        assert "should_archive" in d
        assert "reasons" in d
        assert "scorecard" in d
        assert "comparison" in d


# ---------------------------------------------------------------------------
# compute_scorecard (filesystem)
# ---------------------------------------------------------------------------

class TestComputeScorecard:
    def test_identical_digests(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            kanban_json = {
                "stories": [{"id": 1, "provenance": "tok-1"}, {"id": 2, "provenance": "tok-2"}],
                "categories": [{"name": "AI", "stories": []}],
            }
            batch_json = dict(kanban_json)

            kanban_path = td_path / "kanban.json"
            batch_path = td_path / "batch.json"
            kanban_path.write_text(json.dumps(kanban_json))
            batch_path.write_text(json.dumps(batch_json))

            result = compute_scorecard(kanban_path, batch_path)
            assert result.passed is True
            assert result.story_count.kanban == 2
            assert result.story_count.batch == 2

    def test_different_story_counts(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            kanban_json = {"stories": [{"id": 1}]}
            batch_json = {"stories": [{"id": 1}, {"id": 2}, {"id": 3}]}

            kanban_path = td_path / "kanban.json"
            batch_path = td_path / "batch.json"
            kanban_path.write_text(json.dumps(kanban_json))
            batch_path.write_text(json.dumps(batch_json))

            result = compute_scorecard(kanban_path, batch_path)
            assert result.story_count.kanban == 1
            assert result.story_count.batch == 3


# ---------------------------------------------------------------------------
# compare_diagnostics
# ---------------------------------------------------------------------------

class TestCompareDiagnostics:
    def test_both_none(self):
        comp = compare_diagnostics(None, None, ScorecardResult())
        assert comp.faster_path == "equal"
        assert len(comp.stages) == 0

    def test_with_stages(self):
        kanban_diag = {
            "prefix": "kanban-001",
            "total_duration_ms": 5000,
            "stages": [
                {"id": "research", "duration_ms": 3000},
                {"id": "render", "duration_ms": 2000},
            ],
        }
        batch_diag = {
            "prefix": "batch-001",
            "total_duration_ms": 4000,
            "stages": [
                {"id": "research", "duration_ms": 2500},
                {"id": "render", "duration_ms": 1500},
            ],
        }
        comp = compare_diagnostics(kanban_diag, batch_diag, ScorecardResult())
        assert comp.prefix_kanban == "kanban-001"
        assert comp.prefix_batch == "batch-001"
        assert len(comp.stages) == 2
        # Stages are sorted alphabetically by id, so 'render' < 'research'
        assert comp.stages[0].stage_name == "render"
        assert comp.stages[0].faster == "batch"


# ---------------------------------------------------------------------------
# run_t3c_evaluation (full integration)
# ---------------------------------------------------------------------------

class TestRunT3cEvaluation:
    def test_full_evaluation(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            kanban_diag_dir = td_path / "kanban_diag"
            batch_diag_dir = td_path / "batch_diag"
            kanban_report = td_path / "kanban_report.json"
            batch_report = td_path / "batch_report.json"

            kanban_diag_dir.mkdir()
            batch_diag_dir.mkdir()

            # Create diagnostics files
            kanban_diag = {
                "prefix": "k-001",
                "total_duration_ms": 5000,
                "stages": [{"id": "research", "duration_ms": 3000}],
            }
            batch_diag = {
                "prefix": "b-001",
                "total_duration_ms": 4000,
                "stages": [{"id": "research", "duration_ms": 2500}],
            }
            (kanban_diag_dir / "k-001.diagnostics.json").write_text(json.dumps(kanban_diag))
            (batch_diag_dir / "b-001.diagnostics.json").write_text(json.dumps(batch_diag))

            # Create report files
            kanban_report.write_text(json.dumps({
                "stories": [{"id": 1, "provenance": "tok-1"}],
                "categories": [{"name": "AI", "stories": []}],
            }))
            batch_report.write_text(json.dumps({
                "stories": [{"id": 1, "provenance": "tok-1"}],
                "categories": [{"name": "AI", "stories": []}],
            }))

            result = run_t3c_evaluation(
                kanban_diag_dir=kanban_diag_dir,
                batch_diag_dir=batch_diag_dir,
                kanban_report_path=kanban_report,
                batch_report_path=batch_report,
                prefix_kanban="k-001",
                prefix_batch="b-001",
            )
            assert isinstance(result, ExitCriteriaResult)
            assert result.scorecard is not None
            assert result.comparison is not None
