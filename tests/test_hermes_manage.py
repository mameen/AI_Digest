"""Tests for agentic/hermes/admin/manage.py — real CLI, no mocks."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERMES_MANAGE = [sys.executable, str(ROOT / "agentic" / "hermes" / "admin" / "manage.py")]

_MANAGE_PATH = ROOT / "agentic" / "hermes" / "admin" / "manage.py"
_spec = importlib.util.spec_from_file_location("hermes_manage", _MANAGE_PATH)
assert _spec and _spec.loader
hermes_manage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hermes_manage)

_ARTIFACTS_PATH = ROOT / "agentic" / "hermes" / "tools" / "artifacts.py"
_art_spec = importlib.util.spec_from_file_location("hermes_artifacts", _ARTIFACTS_PATH)
assert _art_spec and _art_spec.loader
hermes_artifacts = importlib.util.module_from_spec(_art_spec)
_art_spec.loader.exec_module(hermes_artifacts)


class HermesManageCliTest(unittest.TestCase):
    def test_status_exits_zero(self) -> None:
        proc = subprocess.run(HERMES_MANAGE + ["status"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("Hermes pkg:", proc.stdout)

    def test_nuke_dry_run_requires_yes(self) -> None:
        proc = subprocess.run(HERMES_MANAGE + ["nuke"], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--yes", proc.stdout)

    def test_setup_dry_run(self) -> None:
        if not shutil.which("hermes"):
            self.skipTest("hermes not on PATH")
        proc = subprocess.run(
            HERMES_MANAGE + ["setup", "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("orio_concierge", proc.stdout)
        self.assertIn("SOUL.md", proc.stdout)
        self.assertIn("would", proc.stdout.lower())

    def test_demo_board_dry_run(self) -> None:
        if not shutil.which("hermes"):
            self.skipTest("hermes not on PATH")
        proc = subprocess.run(
            HERMES_MANAGE + ["demo-board", "--dry-run"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("orio_librarian", proc.stdout)
        self.assertIn("orio_synthesizer", proc.stdout)
        self.assertIn("research × N", proc.stdout)

    def test_generate_report_help(self) -> None:
        proc = subprocess.run(
            HERMES_MANAGE + ["generate-report", "-h"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("generate-report", proc.stdout)

    def test_verify_handover_help(self) -> None:
        proc = subprocess.run(
            HERMES_MANAGE + ["verify-handover", "-h"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("verify-handover", proc.stdout)


class ValidateResearcherArtifactTest(unittest.TestCase):
    def test_missing_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            errors = hermes_artifacts.validate_researcher_artifact(Path(tmp))
            self.assertTrue(errors)

    def test_valid_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "output.md").write_text(
                "- One https://a.example/one\n"
                "- Two https://b.example/two\n"
                "- Three https://c.example/three\n",
                encoding="utf-8",
            )
            self.assertEqual(hermes_artifacts.validate_researcher_artifact(ws), [])


class LibrarianSynthesizerArtifactTest(unittest.TestCase):
    def test_story_url_filters_bare_domain(self) -> None:
        stories = hermes_artifacts._parse_bullet_stories(
            "- Root https://ragaboutit.com/\n"
            "- Good https://example.com/article/one\n"
            "- Also https://example.com/two\n",
            "rag",
        )
        urls = [s.get("url") for s in stories]
        self.assertNotIn("https://ragaboutit.com/", urls)
        self.assertEqual(len(stories), 2)

    def test_showcase_digest_shape(self) -> None:
        hermes_pkg = str(ROOT / "agentic" / "hermes")
        if hermes_pkg not in sys.path:
            sys.path.insert(0, hermes_pkg)
        if str(ROOT) not in sys.path:
            sys.path.insert(0, str(ROOT))
        from tools.showcase import assemble_showcase_digest

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "output.md").write_text(
                "- A https://example.com/one\n- B https://example.com/two\n- C https://example.com/three\n",
                encoding="utf-8",
            )
            research = [{"id": "t1", "title": "Research: aisearch", "workspace_path": str(ws)}]
            digest = assemble_showcase_digest(research, prefix="20260706120000")
            self.assertEqual(len(digest.get("categories") or []), 12)
            aisearch = next(c for c in digest["categories"] if c["id"] == "aisearch")
            self.assertGreaterEqual(len(aisearch.get("stories") or []), 3)
            youtube = next(c for c in digest["categories"] if c["id"] == "youtube")
            self.assertEqual(len(youtube.get("stories") or []), 0)

    def test_librarian_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "librarian.md").write_text(
                "## Topics applied\n\n- **llm** ← `output.md`\n\n"
                "## Merged research\n\n### llm\n\n"
                "- Story https://example.com/one\n- Story https://example.com/two\n",
                encoding="utf-8",
            )
            self.assertEqual(hermes_artifacts.validate_librarian_artifact(ws), [])

    def test_librarian_seed_from_runtime_cache(self) -> None:
        hermes_pkg = str(ROOT / "agentic" / "hermes")
        if hermes_pkg not in sys.path:
            sys.path.insert(0, hermes_pkg)
        import tools.runtime_store as rs
        from tools.runtime_store import persist_research

        with tempfile.TemporaryDirectory() as tmp:
            original = rs.RUNTIME_ROOT
            rs.RUNTIME_ROOT = Path(tmp)
            try:
                prefix = "20260706130000"
                research_ws = Path(tmp) / "research_ws"
                research_ws.mkdir()
                (research_ws / "output.md").write_text(
                    "- A https://example.com/one\n- B https://example.com/two\n- C https://example.com/three\n",
                    encoding="utf-8",
                )
                persist_research(prefix, "llm", research_ws)

                empty_ws = Path(tmp) / "librarian_ws"
                empty_ws.mkdir()
                research = [{"id": "t1", "title": "Research: llm", "workspace_path": str(empty_ws)}]
                result = hermes_artifacts.seed_librarian_artifact(
                    research, empty_ws, prefix=prefix, roles={"agentic_enrich": {"enabled": False}}
                )
                self.assertTrue(result.get("ok"))
                self.assertEqual(result.get("topic_count"), 1)
                self.assertEqual(hermes_artifacts.validate_librarian_artifact(empty_ws), [])
            finally:
                rs.RUNTIME_ROOT = original


class RuntimeStoreTest(unittest.TestCase):
    def test_persist_and_load_digest(self) -> None:
        hermes_pkg = str(ROOT / "agentic" / "hermes")
        if hermes_pkg not in sys.path:
            sys.path.insert(0, hermes_pkg)
        from tools.runtime_store import load_digest, persist_digest_json

        with tempfile.TemporaryDirectory() as tmp:
            import tools.runtime_store as rs

            original = rs.RUNTIME_ROOT
            rs.RUNTIME_ROOT = Path(tmp)
            try:
                digest = {"filename_prefix": "20260706120000", "categories": [], "summary": "x"}
                persist_digest_json("20260706120000", digest)
                loaded = load_digest("20260706120000")
                self.assertEqual(loaded, digest)
            finally:
                rs.RUNTIME_ROOT = original

    def test_stage_librarian_for_workspace(self) -> None:
        hermes_pkg = str(ROOT / "agentic" / "hermes")
        if hermes_pkg not in sys.path:
            sys.path.insert(0, hermes_pkg)
        import tools.runtime_store as rs
        from tools.runtime_store import persist_librarian, stage_librarian_for_workspace

        with tempfile.TemporaryDirectory() as tmp:
            original = rs.RUNTIME_ROOT
            rs.RUNTIME_ROOT = Path(tmp)
            try:
                prefix = "20260706150000"
                lib_ws = Path(tmp) / "lib"
                lib_ws.mkdir()
                (lib_ws / "librarian.md").write_text(
                    "## Topics applied\n\n- **llm**\n\n## Merged research\n\n"
                    "### llm\n\n- Story https://example.com/one\n- Story https://example.com/two\n",
                    encoding="utf-8",
                )
                persist_librarian(prefix, lib_ws)
                synth_ws = Path(tmp) / "synth"
                staged = stage_librarian_for_workspace(prefix, synth_ws)
                self.assertIsNotNone(staged)
                self.assertTrue((synth_ws / "librarian.md").is_file())
            finally:
                rs.RUNTIME_ROOT = original


class HandoverTraceTest(unittest.TestCase):
    def test_extract_urls_and_trace_shape(self) -> None:
        hermes_pkg = str(ROOT / "agentic" / "hermes")
        if hermes_pkg not in sys.path:
            sys.path.insert(0, hermes_pkg)
        from tools.handover_trace import build_handover_trace, extract_urls
        from tools.runtime_store import persist_digest_json, persist_research
        from tools.topics import load_demo_topics

        text = "- One https://example.com/a\n- Two https://example.com/b\n"
        self.assertEqual(
            extract_urls(text),
            ["https://example.com/a", "https://example.com/b"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            import tools.runtime_store as rs

            original = rs.RUNTIME_ROOT
            rs.RUNTIME_ROOT = Path(tmp)
            try:
                prefix = "20260706140000"
                topic = load_demo_topics()[0]
                ws = Path(tmp) / "ws"
                ws.mkdir()
                (ws / "output.md").write_text(text + "- Three https://example.com/c\n", encoding="utf-8")
                persist_research(prefix, topic, ws)
                persist_digest_json(
                    prefix,
                    {
                        "filename_prefix": prefix,
                        "summary": "x",
                        "categories": [
                            {
                                "id": topic,
                                "stories": [{"provenance": f"agent:researcher:{topic}"}],
                            },
                            {
                                "id": "policy",
                                "stories": [{"provenance": "carry:agentic:20260702120000"}],
                            },
                        ],
                    },
                )
                trace = build_handover_trace(prefix)
                topics = {r["topic"] for r in trace["research"]}
                self.assertIn(topic, topics)
                row = next(r for r in trace["research"] if r["topic"] == topic)
                self.assertEqual(len(row["urls"]), 3)
                self.assertTrue(str(row["seed"]).startswith("lib/ingest:"))
                self.assertIn(
                    f"agent:researcher:{topic}",
                    trace["synthesizer"]["digest_provenance"]["totals"],
                )
            finally:
                rs.RUNTIME_ROOT = original


class AgenticOutputPathsTest(unittest.TestCase):
    def test_agentic_reports_and_diagnostics_under_hermes_tree(self) -> None:
        baseline_path = ROOT / "agentic" / "hermes" / "tools" / "baseline.py"
        spec = importlib.util.spec_from_file_location("hermes_baseline", baseline_path)
        assert spec and spec.loader
        baseline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(baseline)

        from lib.paths import AGENTIC_ROOT
        from llm_pipeline.paths import diagnostics_dir, reports_dir

        cfg = baseline.agentic_config()
        self.assertEqual(reports_dir(cfg), AGENTIC_ROOT / "reports")
        self.assertEqual(diagnostics_dir(cfg), AGENTIC_ROOT / "diagnostics")


if __name__ == "__main__":
    unittest.main()
