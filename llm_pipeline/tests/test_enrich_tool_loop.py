"""Fixture-backed tests for remaining llm_pipeline.enrich pure functions.

Tests cover:
- _tool_loop_system: generates system prompt for tool-loop agent
- _tool_loop_user: generates user message with payload + allow_urls
- _coerce_gap_categories: JSON coercion paths (valid JSON, invalid JSON)
- _log_category_counts: prints category counts (tested via capture)
"""

from __future__ import annotations

import json
import unittest
from io import StringIO
from contextlib import redirect_stdout

from llm_pipeline.enrich import (
    _coerce_gap_categories,
    _log_category_counts,
    _tool_loop_system,
    _tool_loop_user,
)


class TestToolLoopSystem(unittest.TestCase):
    """Test _tool_loop_system: generates correct system prompt."""

    def test_basic_tools_no_web_search(self):
        tools = {"verify_url": lambda: None}
        result = _tool_loop_system(tools)
        self.assertIn("citation-verification agent", result)
        self.assertIn('{"action": "verify_url"', result)
        self.assertNotIn("web_search", result)

    def test_web_search_included(self):
        tools = {"verify_url": lambda: None, "web_search": lambda: None}
        result = _tool_loop_system(tools)
        self.assertIn('{"action": "web_search"', result)
        self.assertIn("use web_search to find one", result)

    def test_contains_finalize_action(self):
        tools = {"verify_url": lambda: None}
        result = _tool_loop_system(tools)
        self.assertIn('{"action": "finalize"', result)

    def test_contains_rules_section(self):
        tools = {"verify_url": lambda: None}
        result = _tool_loop_system(tools)
        self.assertIn("Rules:", result)
        self.assertIn("Never invent urls", result)


class TestToolLoopUser(unittest.TestCase):
    """Test _tool_loop_user: generates correct user message."""

    def test_empty_payload(self):
        result = _tool_loop_user([], set())
        self.assertIn("## Gap categories to verify", result)
        self.assertIn("[]", result)
        self.assertIn("(none)", result)

    def test_with_payload(self):
        payload = [{"id": "research", "label": "Research", "stories": []}]
        result = _tool_loop_user(payload, set())
        # The payload JSON is between the first and second blank line
        parts = result.split("\n\n")
        data = json.loads(parts[0].split("\n")[-1])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "research")

    def test_with_allow_urls(self):
        payload = [{"id": "research", "label": "Research", "stories": []}]
        allow_urls = {"https://example.com/1", "https://example.com/2"}
        result = _tool_loop_user(payload, allow_urls)
        self.assertIn("## Known-good source urls", result)
        self.assertIn("https://example.com/1", result)

    def test_truncates_large_allow_sets(self):
        """Allow URLs > 120 should be truncated."""
        payload = [{"id": "research", "label": "Research", "stories": []}]
        allow_urls = {f"https://example.com/{i}" for i in range(200)}
        result = _tool_loop_user(payload, allow_urls)
        # Should contain at most 120 URLs
        url_lines = [
            line for line in result.split("\n")
            if line.startswith("https://")
        ]
        self.assertLessEqual(len(url_lines), 120)


class TestCoerceGapCategories(unittest.TestCase):
    """Test _coerce_gap_categories: JSON coercion paths."""

    def test_valid_json_string(self):
        text = '{"categories": [{"id": "research", "label": "Research", "icon": "", "stories": []}]}'
        result = _coerce_gap_categories(None, None, 0, text)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.categories), 1)
        self.assertEqual(result.categories[0].id, "research")

    def test_valid_json_object(self):
        # model_validate_json expects a string; pass JSON string that parses to object
        text = '{"categories": []}'
        result = _coerce_gap_categories(None, None, 0, text)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.categories), 0)

    def test_invalid_json_returns_none(self):
        result = _coerce_gap_categories(None, None, 0, "not json at all {{{")
        # Should try model_validate_json (fails), model_validate (fails on string),
        # then LLM reformat (fails because no client). Returns None.
        self.assertIsNone(result)

    def test_empty_categories(self):
        text = '{"categories": []}'
        result = _coerce_gap_categories(None, None, 0, text)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.categories), 0)


class TestLogCategoryCounts(unittest.TestCase):
    """Test _log_category_counts: prints category counts."""

    def test_prints_total_and_per_category(self):
        f = StringIO()
        categories = [
            {"id": "research", "stories": [{"id": "1"}]},
            {"id": "aisearch", "stories": []},
        ]
        with redirect_stdout(f):
            _log_category_counts(categories)
        output = f.getvalue()
        self.assertIn("total=1", output)
        self.assertIn("research=1", output)
        self.assertIn("aisearch=0", output)

    def test_empty_categories(self):
        f = StringIO()
        with redirect_stdout(f):
            _log_category_counts([])
        output = f.getvalue()
        self.assertIn("total=0", output)


if __name__ == "__main__":
    unittest.main()
