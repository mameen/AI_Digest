"""Tests for lib.dates — RunWindow, parse_start, prefix_for_start, build_run_window."""

from __future__ import annotations

import unittest
from datetime import date

from lib.dates import (
    RunWindow,
    build_run_window,
    parse_start,
    prefix_for_start,
)


class TestRunWindow(unittest.TestCase):
    """Test RunWindow dataclass and properties."""

    def test_history_from(self):
        window = RunWindow(start=date(2026, 7, 29), history_days=10, prefix="20260729120000")
        self.assertEqual(window.history_from, date(2026, 7, 19))

    def test_history_from_zero_days(self):
        window = RunWindow(start=date(2026, 7, 29), history_days=0, prefix="20260729120000")
        self.assertEqual(window.history_from, date(2026, 7, 29))

    def test_generated_at_is_noon_utc(self):
        window = RunWindow(start=date(2026, 7, 29), history_days=10, prefix="20260729120000")
        self.assertEqual(window.generated_at, "2026-07-29T12:00:00Z")

    def test_label_format(self):
        window = RunWindow(start=date(2026, 7, 29), history_days=10, prefix="20260729120000")
        self.assertEqual(window.label(), "2026-07-19 -> 2026-07-29 (10d)")

    def test_frozen_is_immutable(self):
        window = RunWindow(start=date(2026, 7, 29), history_days=10, prefix="20260729120000")
        with self.assertRaises(Exception):
            window.start = date(2026, 8, 1)


class TestParseStart(unittest.TestCase):
    """Test parse_start: parses YYYY-MM-DD, YYYYMMDD, and 14-digit prefix."""

    def test_none_returns_today(self):
        result = parse_start(None)
        self.assertIsInstance(result, date)

    def test_yyyy_mm_dd_format(self):
        result = parse_start("2026-07-29")
        self.assertEqual(result, date(2026, 7, 29))

    def test_yyyyMMdd_format(self):
        result = parse_start("20260729")
        self.assertEqual(result, date(2026, 7, 29))

    def test_14_digit_prefix(self):
        result = parse_start("20260729120000")
        self.assertEqual(result, date(2026, 7, 29))

    def test_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            parse_start("not-a-date")

    def test_whitespace_stripped(self):
        result = parse_start("  2026-07-29  ")
        self.assertEqual(result, date(2026, 7, 29))

    def test_invalid_month_raises(self):
        with self.assertRaises(ValueError):
            parse_start("2026-13-01")


class TestPrefixForStart(unittest.TestCase):
    """Test prefix_for_start: generates canonical digest prefix."""

    def test_prefix_format(self):
        result = prefix_for_start(date(2026, 7, 29))
        self.assertEqual(result, "20260729120000")

    def test_different_dates_different_prefixes(self):
        p1 = prefix_for_start(date(2026, 7, 28))
        p2 = prefix_for_start(date(2026, 7, 29))
        self.assertNotEqual(p1, p2)


class TestBuildRunWindow(unittest.TestCase):
    """Test build_run_window: creates RunWindow from start string."""

    def test_basic(self):
        window = build_run_window("2026-07-29", 10)
        self.assertEqual(window.start, date(2026, 7, 29))
        self.assertEqual(window.history_days, 10)
        self.assertEqual(window.prefix, "20260729120000")

    def test_none_start(self):
        window = build_run_window(None, 7)
        self.assertIsInstance(window.start, date)
        self.assertEqual(window.history_days, 7)

    def test_negative_history_raises(self):
        with self.assertRaises(ValueError):
            build_run_window("2026-07-29", -1)


if __name__ == "__main__":
    unittest.main()
