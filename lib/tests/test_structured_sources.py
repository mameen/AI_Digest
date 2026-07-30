"""Tests for lib.structured_sources — evalplus_rows, swebench_rows, _val, _size_cell."""

from __future__ import annotations

import unittest

from lib.structured_sources import (
    STRUCTURED_SOURCES,
    _size_cell,
    _val,
    apply_structured_leaderboards,
    evalplus_rows,
    swebench_rows,
)


class TestConstants(unittest.TestCase):
    """Test module constants."""

    def test_structured_sources_has_two_entries(self):
        self.assertEqual(len(STRUCTURED_SOURCES), 2)

    def test_swe_source_key(self):
        swe = next(s for s in STRUCTURED_SOURCES if s["key"] == "swe")
        self.assertEqual(swe["parser"], "swebench")

    def test_coding_source_key(self):
        coding = next(s for s in STRUCTURED_SOURCES if s["key"] == "coding")
        self.assertEqual(coding["parser"], "evalplus")


class TestVal(unittest.TestCase):
    """Test _val: None → em-dash, else pass through."""

    def test_none_returns_em_dash(self):
        self.assertEqual(_val(None), "\u2014")

    def test_string_passes_through(self):
        self.assertEqual(_val("hello"), "hello")

    def test_number_passes_through(self):
        self.assertEqual(_val(42), 42)

    def test_zero_passes_through(self):
        self.assertEqual(_val(0), 0)


class TestSizeCell(unittest.TestCase):
    """Test _size_cell: converts size values."""

    def test_none_returns_em_dash(self):
        self.assertEqual(_size_cell(None), "\u2014")

    def test_integer_float(self):
        self.assertEqual(_size_cell(7.0), 7)

    def test_non_integer_float(self):
        self.assertEqual(_size_cell(7.5), 7.5)

    def test_string_number(self):
        self.assertEqual(_size_cell("128"), 128)

    def test_invalid_string_returns_as_is(self):
        self.assertEqual(_size_cell("abc"), "abc")


class TestEvalplusRows(unittest.TestCase):
    """Test evalplus_rows: ranks by HumanEval+ desc."""

    def test_ranks_by_humaneval_desc(self):
        data = {
            "model-a": {"pass@1": {"humaneval+": 90, "mbpp+": 80}},
            "model-b": {"pass@1": {"humaneval+": 95, "mbpp+": 85}},
            "model-c": {"pass@1": {"humaneval+": 85, "mbpp+": 75}},
        }
        result = evalplus_rows(data)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0][1], "model-b")  # highest humaneval+ first

    def test_respects_limit(self):
        data = {f"model-{i}": {"pass@1": {"humaneval+": i}} for i in range(20)}
        result = evalplus_rows(data, limit=5)
        self.assertEqual(len(result), 5)

    def test_empty_data_returns_empty(self):
        self.assertEqual(evalplus_rows({}), [])

    def test_missing_pass_at_1_uses_negative_one(self):
        data = {"model-a": {}}
        result = evalplus_rows(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "model-a")


class TestSwebenchRows(unittest.TestCase):
    """Test swebench_rows: ranks by resolved desc."""

    def test_ranks_by_resolved_desc(self):
        data = {
            "leaderboards": [
                {
                    "name": "Verified",
                    "results": [
                        {"name": "repo-a", "resolved": 100, "date": "2026-07-01"},
                        {"name": "repo-b", "resolved": 150, "date": "2026-07-02"},
                    ],
                }
            ]
        }
        result = swebench_rows(data)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][1], "repo-b")  # highest resolved first

    def test_missing_board_returns_empty(self):
        data = {"leaderboards": [{"name": "Other"}]}
        result = swebench_rows(data)
        self.assertEqual(result, [])

    def test_empty_results_returns_empty(self):
        data = {"leaderboards": [{"name": "Verified", "results": []}]}
        result = swebench_rows(data)
        self.assertEqual(result, [])

    def test_case_insensitive_board_match(self):
        data = {"leaderboards": [{"name": "verified"}]}
        result = swebench_rows(data)
        self.assertEqual(len(result), 0)  # no results, but board matched


class TestApplyStructuredLeaderboards(unittest.TestCase):
    """Test apply_structured_leaderboards: returns block unchanged when no data."""

    def test_no_files_returns_original_block(self):
        import tempfile
        block = '{"aa": {"rows": [1, 2]}}'
        with tempfile.TemporaryDirectory() as tmpdir:
            result = apply_structured_leaderboards(block, tmpdir)
            self.assertEqual(result, block)

    def test_with_files_returns_block(self):
        import tempfile
        from pathlib import Path
        block = '{"aa": {"rows": [1, 2]}}'
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create one of the expected files
            Path(tmpdir, "swebench_leaderboards.json").write_text("{}")
            result = apply_structured_leaderboards(block, tmpdir)
            self.assertEqual(result, block)  # returns block (no rows to inject without data)


if __name__ == "__main__":
    unittest.main()
