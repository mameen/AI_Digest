"""Tests for lib.tools — parse_tool_action, format_tool_result, looks_not_found, verify_url, _ddg_target, parse_ddg_results."""

from __future__ import annotations

import unittest

from lib.tools import (
    TOOL_CATALOG,
    ToolAction,
    _ddg_target,
    format_tool_result,
    looks_not_found,
    parse_ddg_results,
    parse_tool_action,
    verify_url,
)


class TestToolCatalog(unittest.TestCase):
    """Test TOOL_CATALOG."""

    def test_contains_verify_url(self):
        self.assertIn("verify_url", TOOL_CATALOG)


class TestParseToolAction(unittest.TestCase):
    """Test parse_tool_action: extracts tool action from model text."""

    def test_parses_verify_url_action(self):
        text = 'Here is the action: {"action": "verify_url", "args": {"url": "https://example.com"}}'
        result = parse_tool_action(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "verify_url")
        self.assertEqual(result.args["url"], "https://example.com")

    def test_parses_finalize_action(self):
        text = '{"action": "finalize", "args": {"result": "done"}}'
        result = parse_tool_action(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "finalize")

    def test_parses_with_code_fences(self):
        text = '```json\n{"action": "verify_url", "args": {"url": "https://example.com"}}\n```'
        result = parse_tool_action(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "verify_url")

    def test_returns_none_for_no_json(self):
        result = parse_tool_action("Just some prose text")
        self.assertIsNone(result)

    def test_returns_none_for_empty_text(self):
        result = parse_tool_action("")
        self.assertIsNone(result)

    def test_returns_none_for_missing_action_key(self):
        text = '{"url": "https://example.com"}'
        result = parse_tool_action(text)
        self.assertIsNone(result)

    def test_returns_none_for_empty_action_name(self):
        text = '{"action": "", "args": {}}'
        result = parse_tool_action(text)
        self.assertIsNone(result)

    def test_args_defaults_to_empty_dict(self):
        text = '{"action": "verify_url"}'
        result = parse_tool_action(text)
        self.assertIsNotNone(result)
        self.assertEqual(result.args, {})


class TestFormatToolResult(unittest.TestCase):
    """Test format_tool_result: formats observation message."""

    def test_formats_simple_result(self):
        action = ToolAction(name="verify_url", args={"url": "https://example.com"}, raw="")
        result = format_tool_result(action, {"ok": True})
        self.assertIn("OBSERVATION verify_url:", result)
        self.assertIn('"ok": true', result)

    def test_formats_complex_result(self):
        action = ToolAction(name="web_search", args={"query": "test"}, raw="")
        result = format_tool_result(action, {"results": [{"title": "A"}]})
        self.assertIn("OBSERVATION web_search:", result)


class TestLooksNotFound(unittest.TestCase):
    """Test looks_not_found: detects soft 404 pages."""

    def test_empty_body_returns_false(self):
        self.assertFalse(looks_not_found(""))

    def test_no_body_returns_false(self):
        self.assertFalse(looks_not_found(None))

    def test_normal_page_returns_false(self):
        body = '<html><head><title>AI News - Latest Updates</title></head><body>Hello world</body></html>'
        self.assertFalse(looks_not_found(body))

    def test_404_title_detected(self):
        body = '<html><head><title>404 Not Found</title></head><body>Page not found</body></html>'
        self.assertTrue(looks_not_found(body))

    def test_page_not_found_body_detected(self):
        body = '<html><head><title>Home</title></head><body>The page you requested could not be found</body></html>'
        self.assertTrue(looks_not_found(body))

    def test_404_in_title_detected(self):
        body = '<html><head><title>Error 404 - Page Missing</title></head><body>Oops</body></html>'
        self.assertTrue(looks_not_found(body))


class TestVerifyUrl(unittest.TestCase):
    """Test verify_url: URL liveness check."""

    def test_non_http_url_returns_error(self):
        result = verify_url("ftp://example.com")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "not-an-http-url")

    def test_empty_url_returns_error(self):
        result = verify_url("")
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "not-an-http-url")

    def test_injectable_fetch_called(self):
        def fake_fetch(url, timeout):
            return (200, url, "<html><body>OK</body></html>")
        result = verify_url("https://example.com", fetch=fake_fetch)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], 200)

    def test_soft_404_detected(self):
        def fake_fetch(url, timeout):
            return (200, url, "<html><head><title>Not Found</title></head><body>Page not found</body></html>")
        result = verify_url("https://example.com", fetch=fake_fetch)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "soft-404: page content is 'not found'")

    def test_unreachable_returns_error(self):
        def fake_fetch(url, timeout):
            return (None, url, "")
        result = verify_url("https://example.com", fetch=fake_fetch)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "unreachable")


class TestDdgTarget(unittest.TestCase):
    """Test _ddg_target: resolves DuckDuckGo redirect links."""

    def test_direct_url_passed_through(self):
        result = _ddg_target("https://example.com/article")
        self.assertEqual(result, "https://example.com/article")

    def test_duckduckgo_redirect_resolved(self):
        href = 'https://duckduckgo.com/l/?uddg=https://example.com/target'
        result = _ddg_target(href)
        self.assertEqual(result, "https://example.com/target")

    def test_relative_url_returned_as_none(self):
        # Relative URLs without http(s) prefix are not valid targets
        result = _ddg_target("/article")
        self.assertIsNone(result)


class TestParseDdgResults(unittest.TestCase):
    """Test parse_ddg_results: extracts results from DDG HTML."""

    def test_empty_html_returns_empty(self):
        self.assertEqual(parse_ddg_results(""), [])

    def test_parses_fixture_file(self):
        import os
        fixture_path = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "data", "duckduckgo_html_results.html")
        if os.path.exists(fixture_path):
            html = open(fixture_path, encoding="utf-8").read()
            results = parse_ddg_results(html)
            self.assertIsInstance(results, list)
            if results:
                self.assertIn("title", results[0])
                self.assertIn("url", results[0])


if __name__ == "__main__":
    unittest.main()
