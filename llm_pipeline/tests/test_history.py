"""Fixture-backed tests for llm_pipeline.history — pure functions."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from lib.dates import RunWindow
from llm_pipeline.history import format_prior_context, load_prior_digests


class TestFormatPriorContext(unittest.TestCase):
    """Test format_prior_context: formats prior digests for LLM context."""

    def test_empty_digests_returns_placeholder(self):
        result = format_prior_context([])
        self.assertEqual(result, "(no prior digests in window)")

    def test_formats_single_digest(self):
        digests = [
            {
                "filename_prefix": "20260727120000",
                "summary": "A summary.",
                "categories": [
                    {"id": "research", "stories": [{"id": "1"}]},
                    {"id": "aisearch", "stories": []},
                ],
            }
        ]
        result = format_prior_context(digests)
        self.assertIn("20260727120000", result)
        self.assertIn("A summary.", result)
        self.assertIn("(2 categories, 1 stories)", result)

    def test_formats_multiple_digests(self):
        digests = [
            {
                "filename_prefix": "20260726120000",
                "summary": "Digest A.",
                "categories": [{"id": "research", "stories": []}],
            },
            {
                "filename_prefix": "20260727120000",
                "summary": "Digest B.",
                "categories": [{"id": "research", "stories": []}],
            },
        ]
        result = format_prior_context(digests)
        self.assertIn("20260726120000", result)
        self.assertIn("20260727120000", result)

    def test_respects_max_chars(self):
        digests = [
            {
                "filename_prefix": f"202607{i}120000",
                "summary": "X" * 500,
                "categories": [{"id": "research", "stories": []}],
            }
            for i in range(1, 11)
        ]
        result = format_prior_context(digests, max_chars=200)
        # Should be truncated before all 10 digests fit
        self.assertLess(len(result), sum(len(d["summary"]) for d in digests))

    def test_handles_missing_summary(self):
        digests = [{"filename_prefix": "20260727120000", "categories": []}]
        result = format_prior_context(digests)
        self.assertIn("20260727120000", result)


class TestLoadPriorDigests(unittest.TestCase):
    """Test load_prior_digests: loads prior digests within the lookback window."""

    def test_empty_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = {"output": {"reports_dir": tmpdir}}
            window = MagicMock(spec=RunWindow)
            from datetime import date
            window.start = date(2026, 12, 31)
            window.history_from = date(2026, 1, 1)

            result = load_prior_digests(cfg, window)
            self.assertEqual(result, [])

    def test_filters_by_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a digest within the window
            digest_data = {
                "filename_prefix": "20260727120000",
                "summary": "In-window digest.",
                "categories": [],
            }
            Path(tmpdir, "20260727120000.json").write_text(
                json.dumps(digest_data), encoding="utf-8"
            )

            cfg = {"output": {"reports_dir": tmpdir}}
            window = MagicMock(spec=RunWindow)
            from datetime import date
            window.start = date(2026, 7, 28)
            window.history_from = date(2026, 7, 1)

            result = load_prior_digests(cfg, window)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["summary"], "In-window digest.")

    def test_excludes_digests_on_or_after_window_start(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            digest_data = {
                "filename_prefix": "20260728120000",
                "summary": "On-start digest.",
                "categories": [],
            }
            Path(tmpdir, "20260728120000.json").write_text(
                json.dumps(digest_data), encoding="utf-8"
            )

            cfg = {"output": {"reports_dir": tmpdir}}
            window = MagicMock(spec=RunWindow)
            from datetime import date
            window.start = date(2026, 7, 28)
            window.history_from = date(2026, 7, 1)

            result = load_prior_digests(cfg, window)
            self.assertEqual(result, [])  # excluded (on start date)

    def test_excludes_invalid_prefixes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "index.json").write_text("{}", encoding="utf-8")
            Path(tmpdir, "not-a-date.json").write_text("{}", encoding="utf-8")
            Path(tmpdir, "123456789012345.json").write_text("{}", encoding="utf-8")  # too long

            cfg = {"output": {"reports_dir": tmpdir}}
            window = MagicMock(spec=RunWindow)
            from datetime import date
            window.start = date(2026, 12, 31)
            window.history_from = date(2026, 1, 1)

            result = load_prior_digests(cfg, window)
            self.assertEqual(result, [])  # all invalid

    def test_skips_corrupt_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "20260727120000.json").write_text("not valid json", encoding="utf-8")

            cfg = {"output": {"reports_dir": tmpdir}}
            window = MagicMock(spec=RunWindow)
            from datetime import date
            window.start = date(2026, 12, 31)
            window.history_from = date(2026, 1, 1)

            result = load_prior_digests(cfg, window)
            self.assertEqual(result, [])  # skipped corrupt file

    def test_sorts_by_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for pfx in ["20260729120000", "20260725120000", "20260727120000"]:
                Path(tmpdir, f"{pfx}.json").write_text(
                    json.dumps({"filename_prefix": pfx}), encoding="utf-8"
                )

            cfg = {"output": {"reports_dir": tmpdir}}
            window = MagicMock(spec=RunWindow)
            from datetime import date
            window.start = date(2026, 12, 31)
            window.history_from = date(2026, 7, 1)

            result = load_prior_digests(cfg, window)
            prefixes = [d["filename_prefix"] for d in result]
            self.assertEqual(prefixes, sorted(prefixes))


if __name__ == "__main__":
    unittest.main()
