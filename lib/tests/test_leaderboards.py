"""Tests for lib.leaderboards — parse_aa_models_md, parse_arena_image_md, aa_rows, arena_image_rows, _match_bracket, render_rows_js, replace_field_array."""

from __future__ import annotations

import unittest

from lib.leaderboards import (
    AA_CRAWL_SLUG,
    ARENA_T2I_CRAWL_SLUG,
    _key_span,
    _match_bracket,
    aa_rows,
    arena_image_rows,
    parse_aa_models_md,
    parse_arena_image_md,
    render_rows_js,
    replace_field_array,
    set_field_string,
)


class TestConstants(unittest.TestCase):
    """Test module constants."""

    def test_aa_crawl_slug(self):
        self.assertEqual(AA_CRAWL_SLUG, "artificialanalysis.ai_leaderboards_models.md")

    def test_arena_t2i_crawl_slug(self):
        self.assertEqual(ARENA_T2I_CRAWL_SLUG, "arena.ai_leaderboard_text-to-image.md")


class TestParseAAModelsMd(unittest.TestCase):
    """Test parse_aa_models_md: extracts rows from AA markdown table."""

    def test_parses_valid_table(self):
        md = """
| Model | Context | Provider | Intelligence | Price | Speed | Latency | ... | [Model] |
| llama-3.1-405b | 128K | Meta | 950 | $2.50 | 1200 | 0.8 | ... | [Model] |
""".strip()
        result = parse_aa_models_md(md)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["model"], "llama-3.1-405b")
        self.assertEqual(result[0]["provider"], "Meta")
        self.assertEqual(result[0]["intelligence"], 950)

    def test_parses_multiple_rows(self):
        md = """
| Model | Context | Provider | Intelligence | Price | Speed | Latency | ... | [Model] |
| gpt-4o | 128K | OpenAI | 920 | $5.00 | 800 | 0.5 | ... | [Model] |
| claude-3-opus | 200K | Anthropic | 900 | $7.50 | 600 | 1.2 | ... | [Model] |
""".strip()
        result = parse_aa_models_md(md)
        self.assertEqual(len(result), 2)

    def test_skips_non_table_lines(self):
        md = """
Some header text
| Model | Context | Provider | Intelligence | Price | Speed | Latency | ... | [Model] |
| llama-3.1 | 128K | Meta | 950 | $2.50 | 1200 | 0.8 | ... | [Model] |
Some footer text
""".strip()
        result = parse_aa_models_md(md)
        self.assertEqual(len(result), 1)

    def test_skips_short_rows(self):
        md = "| short | row |"
        result = parse_aa_models_md(md)
        self.assertEqual(result, [])

    def test_skips_missing_model_header(self):
        md = """
| Model | Context | Provider | Intelligence | Price | Speed | Latency | ... | [Other] |
| llama-3.1 | 128K | Meta | 950 | $2.50 | 1200 | 0.8 | ... | [Other] |
""".strip()
        result = parse_aa_models_md(md)
        self.assertEqual(result, [])

    def test_skips_invalid_intelligence(self):
        md = """
| Model | Context | Provider | Intelligence | Price | Speed | Latency | ... | [Model] |
| llama-3.1 | 128K | Meta | N/A | $2.50 | 1200 | 0.8 | ... | [Model] |
""".strip()
        result = parse_aa_models_md(md)
        self.assertEqual(result, [])

    def test_empty_string_returns_empty(self):
        result = parse_aa_models_md("")
        self.assertEqual(result, [])


class TestParseArenaImageMd(unittest.TestCase):
    """Test parse_arena_image_md: extracts rows from arena.ai markdown table."""

    def test_parses_valid_row(self):
        # Arena image format: rank | empty | model_cell | score | votes
        # Parser uses cells[2] as the model cell (markdown link)
        md = "| 1 ||[DALL-E 3](https://openai.com/dall-e-3) OpenAI · CC-BY|85|12000|"
        result = parse_arena_image_md(md)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["rank"], 1)
        self.assertEqual(result[0]["model"], "DALL-E 3")
        self.assertEqual(result[0]["provider"], "OpenAI")
        self.assertEqual(result[0]["score"], 85)

    def test_skips_non_numeric_rank(self):
        md = """
| N/A | [Model](https://example.com) Provider · License | 85 | 12000 |
""".strip()
        result = parse_arena_image_md(md)
        self.assertEqual(result, [])

    def test_skips_short_rows(self):
        md = "| 1 | short |"
        result = parse_arena_image_md(md)
        self.assertEqual(result, [])

    def test_empty_string_returns_empty(self):
        result = parse_arena_image_md("")
        self.assertEqual(result, [])


class TestAaRows(unittest.TestCase):
    """Test aa_rows: maps parsed AA rows to template column order."""

    def test_maps_columns_correctly(self):
        parsed = [{"model": "llama-3.1", "provider": "Meta", "intelligence": 950, "price": "$2.50", "speed": "1200", "latency": "0.8", "context": "128K"}]
        result = aa_rows(parsed, limit=10)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 1)  # rank
        self.assertEqual(result[0][1], "llama-3.1")  # model
        self.assertEqual(result[0][2], "Meta")  # provider
        self.assertEqual(result[0][3], 950)  # intelligence

    def test_respects_limit(self):
        parsed = [{"model": f"model-{i}", "provider": "P", "intelligence": i, "price": "$1", "speed": "100", "latency": "0.1", "context": "C"} for i in range(10)]
        result = aa_rows(parsed, limit=3)
        self.assertEqual(len(result), 3)

    def test_empty_input_returns_empty(self):
        self.assertEqual(aa_rows([], limit=10), [])


class TestArenaImageRows(unittest.TestCase):
    """Test arena_image_rows: maps parsed arena rows sorted by score."""

    def test_sorts_by_score_descending(self):
        parsed = [
            {"model": "A", "provider": "P1", "score": 50, "votes": "100"},
            {"model": "B", "provider": "P2", "score": 90, "votes": "200"},
        ]
        result = arena_image_rows(parsed, limit=10)
        self.assertEqual(result[0][1], "B")  # highest score first

    def test_respects_limit(self):
        parsed = [{"model": f"M{i}", "provider": "P", "score": i, "votes": "1"} for i in range(50)]
        result = arena_image_rows(parsed, limit=5)
        self.assertEqual(len(result), 5)

    def test_empty_input_returns_empty(self):
        self.assertEqual(arena_image_rows([], limit=10), [])


class TestMatchBracket(unittest.TestCase):
    """Test _match_bracket: finds matching bracket pair."""

    def test_matching_braces(self):
        text = '{"a": 1}'
        result = _match_bracket(text, 0, "{", "}")
        self.assertEqual(result, len(text) - 1)

    def test_nested_braces(self):
        text = '{"a": {"b": 2}}'
        result = _match_bracket(text, 0, "{", "}")
        self.assertEqual(result, len(text) - 1)

    def test_with_strings_containing_brackets(self):
        text = '{"key": "value {not a bracket}"}'
        result = _match_bracket(text, 0, "{", "}")
        self.assertEqual(result, len(text) - 1)

    def test_unbalanced_raises(self):
        with self.assertRaises(ValueError):
            _match_bracket('{"a": 1', 0, "{", "}")


class TestKeySpan(unittest.TestCase):
    """Test _key_span: finds key span in JS object literal."""

    def test_finds_existing_key(self):
        # Key must have an object value (regex requires :\s*\{)
        # Keys are unquoted in the regex pattern
        block = '{aa: {rows: [1, 2], label: "test"}}'
        start, end = _key_span(block, "aa")
        self.assertGreaterEqual(start, 0)  # can be 0 at start of string
        self.assertLess(end, len(block))

    def test_finds_nested_key(self):
        # label must have an object value for _key_span to match
        block = '{aa: {rows: [1, 2], nested: {label: "test"}}}'
        start, end = _key_span(block, "nested")
        self.assertGreaterEqual(start, 0)
        self.assertLess(end, len(block))

    def test_missing_key_raises(self):
        block = '{bb: {rows: [1]}}'
        with self.assertRaises(KeyError):
            _key_span(block, "aa")


class TestRenderRowsJs(unittest.TestCase):
    """Test render_rows_js: renders rows as JS array literal."""

    def test_renders_single_row(self):
        result = render_rows_js([[1, "model", "provider", 950]])
        self.assertIn("[", result)
        self.assertIn("]", result)
        self.assertIn('"model"', result)

    def test_renders_multiple_rows(self):
        rows = [[1, "A"], [2, "B"]]
        result = render_rows_js(rows)
        self.assertIn('"A"', result)
        self.assertIn('"B"', result)

    def test_empty_rows(self):
        result = render_rows_js([])
        self.assertIn("[", result)
        self.assertIn("]", result)


class TestReplaceFieldArray(unittest.TestCase):
    """Test replace_field_array: replaces array field in JS object."""

    def test_replaces_existing_field(self):
        # Keys are unquoted in the regex pattern
        block = '{aa: {rows: [1, 2, 3], label: "test"}}'
        result = replace_field_array(block, "aa", "rows", "[4, 5, 6]")
        self.assertIn("[4, 5, 6]", result)
        self.assertNotIn("[1, 2, 3]", result)

    def test_missing_key_returns_original(self):
        block = '{"bb": {"rows": [1]}}'
        result = replace_field_array(block, "aa", "rows", "[4]")
        self.assertEqual(result, block)


class TestSetFieldString(unittest.TestCase):
    """Test set_field_string: replaces string field in JS object."""

    def test_replaces_existing_field(self):
        # Keys are unquoted in the regex pattern
        block = '{aa: {updated: "2026-07-28", label: "test"}}'
        result = set_field_string(block, "aa", "updated", "2026-07-29")
        self.assertIn("2026-07-29", result)

    def test_missing_key_returns_original(self):
        block = '{"bb": {"updated": "2026-07-28"}}'
        result = set_field_string(block, "aa", "updated", "2026-07-29")
        self.assertEqual(result, block)


if __name__ == "__main__":
    unittest.main()
