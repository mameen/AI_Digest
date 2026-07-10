"""Tests for kanban orchestration / Concierge board status."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERMES_PKG = ROOT / "agentic" / "hermes"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERMES_PKG) not in sys.path:
    sys.path.insert(0, str(HERMES_PKG))

from tools.orchestration import (  # noqa: E402
    build_board_navigation,
    detect_run_prefix,
    extract_run_prefix,
    format_status_summary,
    infer_pipeline_phase,
)


class OrchestrationStatusTest(unittest.TestCase):
    def test_extract_run_prefix_from_body(self) -> None:
        body = "Research **leaderboard** (run prefix `20260710061039`)."
        self.assertEqual(extract_run_prefix(body), "20260710061039")

    def test_detect_run_prefix_from_rows(self) -> None:
        rows = [
            {"title": "Research: youtube", "body": "run prefix `20260709120000`"},
            {"title": "Librarian: merge & classify", "body": "other"},
        ]
        self.assertEqual(detect_run_prefix(rows), "20260709120000")

    def test_infer_phase_research(self) -> None:
        phase = infer_pipeline_phase(
            board_empty=False,
            research={"count": 3, "done": 1},
            librarian={"kanban_done": False},
            synthesizer={"kanban_done": False},
            report_ready=False,
        )
        self.assertEqual(phase, "research")

    def test_infer_phase_librarian(self) -> None:
        phase = infer_pipeline_phase(
            board_empty=False,
            research={"count": 3, "done": 3},
            librarian={"kanban_done": False},
            synthesizer={"kanban_done": False},
            report_ready=False,
        )
        self.assertEqual(phase, "librarian")

    def test_infer_phase_blocked_when_synth_gate_fails(self) -> None:
        phase = infer_pipeline_phase(
            board_empty=False,
            research={"count": 12, "done": 12},
            librarian={"kanban_done": True, "gate_ok": True},
            synthesizer={"kanban_done": True, "gate_ok": False},
            report_ready=False,
            pipeline_artifacts_ok=False,
        )
        self.assertEqual(phase, "blocked")

    def test_format_summary_blocked_not_ready_for_render(self) -> None:
        lines = format_status_summary(
            {
                "board_empty": False,
                "run_prefix": "20260709120000",
                "phase": "blocked",
                "pipeline_artifacts_ok": False,
                "report_ready": False,
                "status_counts": {"done": 14},
                "research": {"count": 12, "done": 12, "artifact_pass": 12, "all_pass": True},
                "librarian": {"count": 1, "done": 1, "all_pass": True},
                "synthesizer": {"count": 1, "done": 1, "all_pass": False},
                "tasks": [
                    {
                        "title": "Synthesize digest",
                        "errors": ["missing digest.json"],
                    }
                ],
            }
        )
        self.assertTrue(any("NOT ready for render" in line for line in lines))
        self.assertTrue(any("BLOCKED" in line for line in lines))
        self.assertFalse(any("Workers finished" in line for line in lines))

    def test_format_summary_includes_phase(self) -> None:
        lines = format_status_summary(
            {
                "board_empty": False,
                "run_prefix": "20260710061039",
                "phase": "research",
                "status_counts": {"done": 5, "running": 1, "todo": 6},
                "research": {"count": 12, "done": 5, "artifact_pass": 5},
                "librarian": {"count": 1, "done": 0, "all_pass": False},
                "synthesizer": {"count": 1, "done": 0, "all_pass": False},
                "active_tasks": [
                    {"status": "running", "title": "Research: robotics", "assignee": "orio_researcher"}
                ],
                "board_navigation": {
                    "primary_anchor": {
                        "id": "t_lib",
                        "title": "Librarian: merge & classify",
                        "status": "todo",
                        "kanban_show": "hermes kanban show t_lib",
                    },
                    "root_tasks": [
                        {
                            "id": "t_root",
                            "title": "Research: leaderboard",
                            "status": "done",
                            "kanban_show": "hermes kanban show t_root",
                        }
                    ],
                    "list_cmd": "hermes kanban list --json",
                },
            }
        )
        self.assertTrue(any("20260710061039" in line for line in lines))
        self.assertTrue(any("research fan-out" in line for line in lines))
        self.assertTrue(any("Research: robotics" in line for line in lines))
        self.assertTrue(any("t_lib" in line for line in lines))
        self.assertTrue(any("t_root" in line for line in lines))

    def test_build_board_navigation(self) -> None:
        rows = [
            {"id": "t_r1", "title": "Research: youtube", "status": "done", "assignee": "orio_researcher"},
            {"id": "t_lib", "title": "Librarian: merge & classify", "status": "todo", "assignee": "orio_librarian"},
            {"id": "t_syn", "title": "Synthesize digest", "status": "todo", "assignee": "orio_synthesizer"},
        ]
        nav = build_board_navigation(rows)
        self.assertEqual(nav["primary_anchor"]["id"], "t_lib")
        self.assertEqual(len(nav["root_tasks"]), 1)
        self.assertEqual(nav["root_tasks"][0]["id"], "t_r1")
        self.assertEqual(nav["synthesizer"]["id"], "t_syn")


class BoardStatusLiveTest(unittest.TestCase):
    def test_board_status_live_when_hermes_available(self) -> None:
        import shutil

        if not shutil.which("hermes"):
            self.skipTest("hermes not on PATH")
        from tools.orchestration import board_status

        payload = board_status(brief=True)
        self.assertTrue(payload.get("ok"), payload)
        self.assertIn("summary", payload)
        self.assertIsInstance(payload["summary"], list)
        self.assertGreater(len(payload["summary"]), 0)


if __name__ == "__main__":
    unittest.main()
