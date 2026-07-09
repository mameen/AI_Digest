"""Tests for admin/manage.py — real CLI, no mocks."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANAGE = [sys.executable, str(ROOT / "admin" / "manage.py")]


class ManageCliTest(unittest.TestCase):
    def test_status_exits_zero(self) -> None:
        proc = subprocess.run(MANAGE + ["status"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        self.assertIn("Repo:", proc.stdout)

    def test_nuke_ephemeral_dry_run_requires_yes(self) -> None:
        proc = subprocess.run(MANAGE + ["nuke", "ephemeral"], cwd=ROOT, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("--yes", proc.stdout)


if __name__ == "__main__":
    unittest.main()
