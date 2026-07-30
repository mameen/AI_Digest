"""Tests for llm_pipeline.dates — run date and history window helpers."""

from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from lib.dates import (
    RunWindow,
    build_run_window,
    parse_start,
    prefix_for_start,
)


class TestRunWindow(unittest.TestCase):
    """Tests for the RunWindow dataclass and its properties."""

    def test_history_from_returns_correct_date(self):
        """history_from should be start minus history_days."""
        window = RunWindow(start=date(2026, 7, 28), history_days=7, prefix="20260728120000")
        self.assertEqual(window.history_from, date(2026, 7, 21))

    def test_history_from_zero_days(self):
        """When history_days is 0, history_from equals start."""
        window = RunWindow(start=date(2026, 7, 28), history_days=0, prefix="20260728120000")
        self.assertEqual(window.history_from, date(2026, 7, 28))

    def test_history_from_large_window(self):
        """Large history window should span correctly across month boundaries."""
        window = RunWindow(start=date(2026, 3, 1), history_days=60, prefix="20260301120000")
        self.assertEqual(window.history_from, date(2025, 12, 31))

    def test_generated_at_returns_noon_utc_iso(self):
        """generated_at should return noon UTC in ISO format."""
        window = RunWindow(start=date(2026, 7, 28), history_days=7, prefix="20260728120000")
        self.assertEqual(window.generated_at, "2026-07-28T12:00:00Z")

    def test_generated_at_midnight_boundary(self):
        """generated_at should handle midnight dates correctly."""
        window = RunWindow(start=date(2026, 1, 1), history_days=30, prefix="20260101120000")
        self.assertEqual(window.generated_at, "2026-01-01T12:00:00Z")

    def test_label_format(self):
        """label should show history_from -> start (N days)."""
        window = RunWindow(start=date(2026, 7, 28), history_days=7, prefix="20260728120000")
        self.assertEqual(window.label(), "2026-07-21 -> 2026-07-28 (7d)")

    def test_label_zero_days(self):
        """label should show same date when history_days is 0."""
        window = RunWindow(start=date(2026, 7, 28), history_days=0, prefix="20260728120000")
        self.assertEqual(window.label(), "2026-07-28 -> 2026-07-28 (0d)")

    def test_runwindow_is_frozen(self):
        """RunWindow should be immutable (frozen dataclass)."""
        window = RunWindow(start=date(2026, 7, 28), history_days=7, prefix="20260728120000")
        with self.assertRaises(Exception):
            window.start = date(2026, 7, 29)


class TestParseStart(unittest.TestCase):
    """Tests for the parse_start function."""

    def test_none_returns_today(self):
        """parse_start(None) should return today's date."""
        with patch("lib.dates.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 28, 12, 0, 0)
            result = parse_start(None)
            self.assertEqual(result, date(2026, 7, 28))

    def test_dash_separated_date(self):
        """parse_start should handle YYYY-MM-DD format."""
        result = parse_start("2026-07-28")
        self.assertEqual(result, date(2026, 7, 28))

    def test_no_separator_date(self):
        """parse_start should handle YYYYMMDD format."""
        result = parse_start("20260728")
        self.assertEqual(result, date(2026, 7, 28))

    def test_14_digit_prefix(self):
        """parse_start should handle 14-digit prefix (YYYYMMDDHHMMSS)."""
        result = parse_start("20260728120000")
        self.assertEqual(result, date(2026, 7, 28))

    def test_whitespace_stripped(self):
        """parse_start should strip whitespace from input."""
        result = parse_start("  2026-07-28  ")
        self.assertEqual(result, date(2026, 7, 28))

    def test_invalid_date_raises_value_error(self):
        """parse_start should raise ValueError for invalid dates."""
        with self.assertRaises(ValueError) as ctx:
            parse_start("invalid")
        self.assertIn("invalid start date", str(ctx.exception))

    def test_partial_date_raises_value_error(self):
        """parse_start should raise ValueError for partial dates like YYYY-MM."""
        with self.assertRaises(ValueError):
            parse_start("2026-07")

    def test_short_prefix_raises_value_error(self):
        """parse_start should raise ValueError for short prefixes."""
        with self.assertRaises(ValueError):
            parse_start("202607")


class TestPrefixForStart(unittest.TestCase):
    """Tests for the prefix_for_start function."""

    def test_prefix_format(self):
        """prefix_for_start should return YYYYMMDD120000 format."""
        result = prefix_for_start(date(2026, 7, 28))
        self.assertEqual(result, "20260728120000")

    def test_prefix_january(self):
        """prefix_for_start should handle January dates correctly."""
        result = prefix_for_start(date(2026, 1, 1))
        self.assertEqual(result, "20260101120000")

    def test_prefix_leap_year(self):
        """prefix_for_start should handle leap year dates correctly."""
        result = prefix_for_start(date(2024, 2, 29))
        self.assertEqual(result, "20240229120000")


class TestBuildRunWindow(unittest.TestCase):
    """Tests for the build_run_window function."""

    def test_build_run_window_basic(self):
        """build_run_window should create a RunWindow with correct values."""
        window = build_run_window("2026-07-28", 7)
        self.assertEqual(window.start, date(2026, 7, 28))
        self.assertEqual(window.history_days, 7)
        self.assertEqual(window.prefix, "20260728120000")

    def test_build_run_window_with_prefix(self):
        """build_run_window should handle 14-digit prefix input."""
        window = build_run_window("20260728120000", 14)
        self.assertEqual(window.start, date(2026, 7, 28))
        self.assertEqual(window.history_days, 14)

    def test_build_run_window_none_start(self):
        """build_run_window should handle None start (defaults to today)."""
        with patch("lib.dates.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 7, 28, 12, 0, 0)
            window = build_run_window(None, 7)
            self.assertEqual(window.start, date(2026, 7, 28))

    def test_build_run_window_negative_history_raises(self):
        """build_run_window should raise ValueError for negative history_days."""
        with self.assertRaises(ValueError) as ctx:
            build_run_window("2026-07-28", -1)
        self.assertIn("history must be >= 0", str(ctx.exception))

    def test_build_run_window_zero_history(self):
        """build_run_window should handle zero history_days."""
        window = build_run_window("2026-07-28", 0)
        self.assertEqual(window.history_days, 0)
        self.assertEqual(window.history_from, date(2026, 7, 28))

    def test_build_run_window_large_history(self):
        """build_run_window should handle large history_days."""
        window = build_run_window("2026-03-01", 90)
        self.assertEqual(window.history_from, date(2025, 12, 1))


if __name__ == "__main__":
    unittest.main()
