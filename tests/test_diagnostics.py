"""Stage error capture + graceful degradation, exercised on the real collector.

No mocks: a real ``DiagnosticCollector`` runs stages via its own context
manager, and the resulting report/HTML are the actual artifacts the pipeline
writes — we only assert on their contents.
"""

from __future__ import annotations

import unittest

from pipeline.diagnostics import (
    DiagnosticCollector,
    _render_run_log,
    _render_waterfall_html,
)


def _collector() -> DiagnosticCollector:
    return DiagnosticCollector(prefix="20260101120000", cfg={}, enabled=True)


class CriticalStage(unittest.TestCase):
    def test_success_marks_ok(self) -> None:
        col = _collector()
        with col.stage("ingestion", "Ingestion") as rec:
            pass
        self.assertTrue(rec.ok)
        self.assertIsNone(rec.error)

    def test_failure_reraises_and_records(self) -> None:
        col = _collector()
        with self.assertRaises(ValueError):
            with col.stage("enrich", "Enrich"):
                raise ValueError("model collapsed")
        rec = col.stages[-1]
        self.assertFalse(rec.ok)
        self.assertIn("model collapsed", rec.error or "")
        self.assertTrue(rec.critical)


class NonCriticalStage(unittest.TestCase):
    def test_failure_is_swallowed_but_recorded(self) -> None:
        col = _collector()
        # Must NOT raise — a flaky source degrades rather than sinking the run.
        with col.stage("ingestion.crawl4ai", "Crawl4AI", critical=False):
            raise RuntimeError("leaderboard host down")
        rec = col.stages[-1]
        self.assertFalse(rec.ok)
        self.assertFalse(rec.critical)
        self.assertIn("leaderboard host down", rec.error or "")

    def test_run_continues_after_degraded_stage(self) -> None:
        col = _collector()
        with col.stage("ingestion.crawl4ai", "Crawl4AI", critical=False):
            raise RuntimeError("boom")
        reached = False
        with col.stage("render", "Render"):
            reached = True
        self.assertTrue(reached)
        self.assertTrue(col.stages[-1].ok)


class ReportStatus(unittest.TestCase):
    def test_all_ok_is_status_ok(self) -> None:
        col = _collector()
        with col.stage("ingestion", "Ingestion"):
            pass
        report = col.build_report()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["totals"]["stage_failures"], 0)
        self.assertEqual(report["totals"]["failed_stages"], [])

    def test_degraded_lists_failed_stage(self) -> None:
        col = _collector()
        with col.stage("ingestion.crawl4ai", "Crawl4AI", critical=False):
            raise RuntimeError("boom")
        report = col.build_report()
        self.assertEqual(report["status"], "degraded")
        self.assertEqual(report["totals"]["stage_failures"], 1)
        self.assertIn("ingestion.crawl4ai", report["totals"]["failed_stages"])

    def test_nested_child_failure_is_detected(self) -> None:
        col = _collector()
        with col.stage("ingestion", "Ingestion"):
            with col.stage("ingestion.structured", "Structured", critical=False):
                raise RuntimeError("api 500")
        report = col.build_report()
        self.assertEqual(report["status"], "degraded")
        self.assertIn("ingestion.structured", report["totals"]["failed_stages"])


class WaterfallHtml(unittest.TestCase):
    def test_failed_stage_is_surfaced_in_html(self) -> None:
        col = _collector()
        with col.stage("ingestion.crawl4ai", "Crawl4AI", critical=False):
            raise RuntimeError("leaderboard host down")
        html = _render_waterfall_html(col.build_report())
        self.assertIn("degraded", html)
        self.assertIn("leaderboard host down", html)  # error shown in row title

    def test_critical_failure_labelled_failed_in_html(self) -> None:
        col = _collector()
        try:
            with col.stage("enrich", "Enrich"):
                raise ValueError("model collapsed")
        except ValueError:
            pass
        html = _render_waterfall_html(col.build_report())
        self.assertIn("FAILED", html)


class Logging(unittest.TestCase):
    def test_log_line_records_level_and_stage(self) -> None:
        col = _collector()
        col.log("starting up")  # no stage
        with col.stage("enrich", "Enrich"):
            col.log("model slow", level="warn")
        self.assertEqual([l.message for l in col.logs], ["starting up", "model slow"])
        self.assertEqual(col.logs[0].stage, None)
        self.assertEqual(col.logs[1].stage, "enrich")
        self.assertEqual(col.logs[1].level, "WARN")

    def test_stage_failure_emits_log_line(self) -> None:
        col = _collector()
        with col.stage("ingestion.crawl4ai", "Crawl4AI", critical=False):
            raise RuntimeError("host down")
        levels = {l.level for l in col.logs}
        self.assertIn("WARN", levels)
        self.assertTrue(any("host down" in l.message for l in col.logs))

    def test_report_carries_log(self) -> None:
        col = _collector()
        col.log("hello")
        report = col.build_report()
        self.assertEqual(report["log"][0]["message"], "hello")


class RunLogText(unittest.TestCase):
    def test_plaintext_has_header_and_lines(self) -> None:
        col = _collector()
        with col.stage("render", "Render"):
            col.log("wrote html")
        text = _render_run_log(col.build_report())
        self.assertIn("# AI Digest run log", text)
        self.assertIn("status=ok", text)
        self.assertIn("[render]", text)
        self.assertIn("wrote html", text)

    def test_degraded_status_in_header(self) -> None:
        col = _collector()
        with col.stage("ingestion.structured", "Structured", critical=False):
            raise RuntimeError("api 500")
        text = _render_run_log(col.build_report())
        self.assertIn("status=degraded", text)


if __name__ == "__main__":
    unittest.main()
