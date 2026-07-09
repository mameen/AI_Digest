"""Agent diagnostics rebuild from handover fixtures."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERMES = ROOT / "agentic" / "hermes"
if str(HERMES) not in sys.path:
    sys.path.insert(0, str(HERMES))

from tools.agent_diagnostics import rebuild_from_artifacts  # noqa: E402


class AgentDiagnosticsRebuild(unittest.TestCase):
    def test_rebuild_from_handover_fixture(self) -> None:
        src_prefix = "20260707182407"
        src_handover = HERMES / ".runtime" / "artifacts" / src_prefix / "handover.json"
        if not src_handover.is_file():
            self.skipTest("E2E handover fixture not present locally")

        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / ".runtime" / "artifacts" / src_prefix
            runtime.mkdir(parents=True)
            shutil.copy2(src_handover, runtime / "handover.json")
            for name in ("digest.json", "librarian.md"):
                src = HERMES / ".runtime" / "artifacts" / src_prefix / name
                if src.is_file():
                    shutil.copy2(src, runtime / name)
            research = HERMES / ".runtime" / "artifacts" / src_prefix / "research"
            if research.is_dir():
                shutil.copytree(research, runtime / "research")

            # Point module RUNTIME at temp tree
            import tools.agent_diagnostics as ad

            old_runtime = ad.RUNTIME
            ad.RUNTIME = Path(tmp) / ".runtime"
            try:
                path = rebuild_from_artifacts(src_prefix)
            finally:
                ad.RUNTIME = old_runtime

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["schema"], "agentic_hermes.diagnostics/v1")
            self.assertEqual(data["prefix"], src_prefix)
            labels = [s["label"] for s in data["stages"]]
            self.assertIn("Research workers", labels)
            self.assertIn("Synthesizer · digest JSON", labels)
            self.assertGreaterEqual(data["totals"]["task_count"], 3)


class DiagnosticsHeatmapIntensity(unittest.TestCase):
    def test_duration_only_runs_score_visible(self) -> None:
        from llm_pipeline.diagnostics_frame import _intensity_score

        # Hermes E2E: ~16.4m wall time, no token telemetry in diagnostics JSON
        score = _intensity_score(983_500, 0)
        self.assertGreater(score, 0.6)
        self.assertLessEqual(score, 1.0)


if __name__ == "__main__":
    unittest.main()
