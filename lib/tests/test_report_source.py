"""Report source badge paths and stamping."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lib.report_source import (
    REPORT_SOURCE_HERMES,
    REPORT_SOURCE_LLM,
    badge_href,
    detect_context_from_reports_dir,
    detect_source_from_cfg,
    stamp_document,
    stamp_json_file,
    stamp_reports_tree,
)


class ReportSource(unittest.TestCase):
    def test_badge_hrefs(self) -> None:
        self.assertIn("docs/img/llm_pipeline", badge_href(REPORT_SOURCE_LLM, "llm_pipeline"))
        self.assertIn("hermes-agent.png", badge_href(REPORT_SOURCE_HERMES, "agentic_hermes"))
        self.assertEqual(
            badge_href(REPORT_SOURCE_LLM, "app"),
            "../img/report-source/llm_pipeline.png",
        )

    def test_detect_source_from_cfg(self) -> None:
        self.assertEqual(
            detect_source_from_cfg({"output": {"root": "agentic/hermes"}}),
            REPORT_SOURCE_HERMES,
        )
        self.assertEqual(detect_source_from_cfg({}), REPORT_SOURCE_LLM)

    def test_detect_context_from_reports_dir(self) -> None:
        self.assertEqual(
            detect_context_from_reports_dir(Path("/repo/app/reports")),
            "app",
        )
        self.assertEqual(
            detect_context_from_reports_dir(Path("/repo/agentic/hermes/reports")),
            "agentic_hermes",
        )

    def test_stamp_document_adds_fields(self) -> None:
        out = stamp_document({"summary": "x"}, REPORT_SOURCE_HERMES, "agentic_hermes")
        self.assertEqual(out["report_source"], REPORT_SOURCE_HERMES)
        self.assertEqual(out["report_source_label"], "Hermes Agent")
        self.assertIn("hermes-agent.png", out["report_source_badge"])

    def test_stamp_reports_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            sample = {"generated_at": "2026-07-07T12:00:00Z", "summary": "s", "categories": []}
            (reports / "20260707120000.json").write_text(json.dumps(sample), encoding="utf-8")
            (reports / "20260707120000.html").write_text("<html></html>", encoding="utf-8")
            n = stamp_reports_tree(reports, source=REPORT_SOURCE_LLM, context="llm_pipeline")
            self.assertEqual(n, 1)
            data = json.loads((reports / "20260707120000.json").read_text(encoding="utf-8"))
            self.assertEqual(data["report_source"], REPORT_SOURCE_LLM)

    def test_infer_agentic_only_prefix_in_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            agentic = repo / "agentic" / "hermes" / "reports"
            app_reports = repo / "app" / "reports"
            agentic.mkdir(parents=True)
            app_reports.mkdir(parents=True)
            sample = {"generated_at": "2026-07-07T12:00:00Z", "summary": "s", "categories": []}
            (agentic / "20260707182407.json").write_text(json.dumps(sample), encoding="utf-8")
            (app_reports / "20260707182407.json").write_text(json.dumps(sample), encoding="utf-8")
            (app_reports / "20260707182407.html").write_text("<html></html>", encoding="utf-8")
            n = stamp_reports_tree(app_reports, source=None, context="app")
            self.assertEqual(n, 1)
            data = json.loads((app_reports / "20260707182407.json").read_text(encoding="utf-8"))
            self.assertEqual(data["report_source"], REPORT_SOURCE_HERMES)
            self.assertIn("hermes-agent.png", data["report_source_badge"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "20260707120000.json"
            path.write_text('{"summary":"s","categories":[]}\n', encoding="utf-8")
            self.assertTrue(stamp_json_file(path, source=REPORT_SOURCE_LLM, context="llm_pipeline"))
            self.assertFalse(stamp_json_file(path, source=REPORT_SOURCE_LLM, context="llm_pipeline"))


if __name__ == "__main__":
    unittest.main()
