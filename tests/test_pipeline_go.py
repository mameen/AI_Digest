"""Tests for batch pipeline GO (--pipeline) — dry-run and window math."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERMES = ROOT / "agentic" / "hermes"
if str(HERMES) not in sys.path:
    sys.path.insert(0, str(HERMES))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HERMES_MANAGE = [sys.executable, str(HERMES / "admin" / "manage.py")]

_spec = importlib.util.spec_from_file_location("pipeline_go", HERMES / "tools" / "pipeline_go.py")
assert _spec and _spec.loader
pipeline_go = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pipeline_go)

_scaffold_spec = importlib.util.spec_from_file_location(
    "digest_scaffold", HERMES / "tools" / "digest_scaffold.py"
)
assert _scaffold_spec and _scaffold_spec.loader
digest_scaffold = importlib.util.module_from_spec(_scaffold_spec)
_scaffold_spec.loader.exec_module(digest_scaffold)


class PipelineGoWindowTest(unittest.TestCase):
    def test_resolve_go_window_noon_prefix(self) -> None:
        window, prefix = pipeline_go.resolve_go_window(start="2026-07-09", history=10)
        self.assertEqual(prefix, "20260709120000")
        self.assertEqual(window.history_days, 10)
        self.assertIn("2026-06-29", window.label())

    def test_explicit_prefix_overrides_window(self) -> None:
        _, prefix = pipeline_go.resolve_go_window(
            start="2026-07-09",
            history=10,
            prefix="20260710030714",
        )
        self.assertEqual(prefix, "20260710030714")

    def test_dry_run_does_not_fetch(self) -> None:
        result = pipeline_go.run_production_pipeline(
            start="2026-07-09",
            history=10,
            dry_run=True,
        )
        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("dry_run"))
        self.assertEqual(result.get("prefix"), "20260709120000")


class DigestScaffoldTest(unittest.TestCase):
    def test_empty_digest_has_twelve_categories(self) -> None:
        digest = digest_scaffold.empty_digest("20260709120000")
        self.assertEqual(digest["filename_prefix"], "20260709120000")
        self.assertEqual(len(digest.get("categories") or []), 12)
        self.assertEqual(
            sum(len(c.get("stories") or []) for c in digest["categories"]),
            0,
        )


class PipelineGoCliTest(unittest.TestCase):
    def test_go_help_lists_pipeline_flags(self) -> None:
        proc = subprocess.run(
            HERMES_MANAGE + ["go", "-h"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("--start", proc.stdout)
        self.assertIn("--history", proc.stdout)
        self.assertIn("--pipeline", proc.stdout)
        self.assertIn("kanban", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()
