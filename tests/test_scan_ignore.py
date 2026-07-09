#!/usr/bin/env python3
"""Tests for .piiignore / .ignorepii path matching."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_spec = importlib.util.spec_from_file_location("scan_ignore", _SCRIPTS / "scan_ignore.py")
assert _spec and _spec.loader
scan_ignore = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan_ignore)


class ScanIgnoreTest(unittest.TestCase):
    def test_kb_exempt(self) -> None:
        patterns = scan_ignore.load_patterns(ROOT)
        self.assertTrue(scan_ignore.is_ignored("agentic/hermes/.kb/private/goals.md", patterns))
        self.assertTrue(scan_ignore.is_ignored(".kb/public/resume.md", patterns))

    def test_source_not_exempt(self) -> None:
        patterns = scan_ignore.load_patterns(ROOT)
        self.assertFalse(scan_ignore.is_ignored("agentic/hermes/admin/manage.py", patterns))

    def test_fixture_exempt(self) -> None:
        patterns = scan_ignore.load_patterns(ROOT)
        self.assertTrue(scan_ignore.is_ignored("tests/fixtures/recruiter_sample.eml", patterns))


if __name__ == "__main__":
    unittest.main()
