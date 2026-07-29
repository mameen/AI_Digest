"""Fixture-backed tests for remaining llm_pipeline.enrich pure functions.

Tests cover:
- _merge_skeleton_fields: copies deterministic fields from skeleton to enriched stories
- _skeleton_rules: returns rules string per category
- _apply_target_count: trims stories to target count (when len <= target)
"""

from __future__ import annotations

import unittest

from llm_pipeline.enrich import (
    _apply_target_count,
    _merge_skeleton_fields,
    _skeleton_rules,
)


class TestMergeSkeletonFields(unittest.TestCase):
    """Test _merge_skeleton_fields: copies deterministic fields from skeleton to enriched."""

    def test_copies_matching_field(self):
        enriched = [{"id": "1", "title": "A"}, {"id": "2", "title": "B"}]
        skeleton = [
            {"id": "1", "links": ["https://example.com/1"]},
            {"id": "2", "links": ["https://example.com/2"]},
        ]
        result = _merge_skeleton_fields(enriched, skeleton, "links")
        self.assertEqual(result[0]["links"], ["https://example.com/1"])
        self.assertEqual(result[1]["links"], ["https://example.com/2"])

    def test_skips_missing_ids(self):
        enriched = [{"id": "1", "title": "A"}, {"id": "99", "title": "X"}]
        skeleton = [
            {"id": "1", "links": ["https://example.com/1"]},
        ]
        result = _merge_skeleton_fields(enriched, skeleton, "links")
        self.assertEqual(result[0]["links"], ["https://example.com/1"])
        self.assertNotIn("links", result[1])  # id 99 not in skeleton

    def test_skips_empty_values(self):
        enriched = [{"id": "1", "title": "A"}]
        skeleton = [
            {"id": "1", "links": []},  # empty list is falsy, should be skipped
        ]
        result = _merge_skeleton_fields(enriched, skeleton, "links")
        self.assertNotIn("links", result[0])

    def test_multiple_fields(self):
        enriched = [{"id": "1", "title": "A"}]
        skeleton = [
            {"id": "1", "links": ["https://example.com"], "tags": ["ai"]},
        ]
        result = _merge_skeleton_fields(enriched, skeleton, "links", "tags")
        self.assertEqual(result[0]["links"], ["https://example.com"])
        self.assertEqual(result[0]["tags"], ["ai"])

    def test_empty_enriched_is_noop(self):
        result = _merge_skeleton_fields([], [{"id": "1"}], "links")
        self.assertEqual(result, [])

    def test_empty_skeleton_is_noop(self):
        enriched = [{"id": "1", "title": "A"}]
        result = _merge_skeleton_fields(enriched, [], "links")
        self.assertEqual(len(result), 1)
        self.assertNotIn("links", result[0])


class TestSkeletonRules(unittest.TestCase):
    """Test _skeleton_rules: returns rules string per category."""

    def test_aisearch_curate_after(self):
        rules = _skeleton_rules("aisearch", curate_after=True)
        self.assertIn("Enrich every chapter", rules)

    def test_aisearch_no_curate(self):
        rules = _skeleton_rules("aisearch", curate_after=False)
        self.assertIn("CRITICAL: return exactly the same number of stories", rules)
        self.assertIn("do not invent urls", rules)

    def test_youtube_rules(self):
        rules = _skeleton_rules("youtube")
        self.assertIn("CRITICAL: return exactly the same number of stories", rules)
        self.assertIn("do not invent urls", rules)

    def test_typography_rules(self):
        rules = _skeleton_rules("typography")
        self.assertIn("Keep ids and urls exactly", rules)
        self.assertIn("Prioritize text rendering", rules)

    def test_research_rules(self):
        rules = _skeleton_rules("research")
        self.assertIn("Score papers by significance", rules)

    def test_robotics_rules(self):
        rules = _skeleton_rules("robotics")
        self.assertIn("Prioritize humanoid/embodied AI", rules)

    def test_unknown_category_returns_empty(self):
        rules = _skeleton_rules("unknown-category")
        self.assertEqual(rules, "")


class TestApplyTargetCount(unittest.TestCase):
    """Test _apply_target_count: trims stories to target count."""

    def test_no_target_returns_all(self):
        stories = [{"id": "1"}, {"id": "2"}]
        result = _apply_target_count(None, None, 0, "test", "Test", stories, None, "")
        self.assertEqual(len(result), 2)

    def test_target_none_returns_all(self):
        stories = [{"id": "1"}, {"id": "2"}]
        result = _apply_target_count(None, None, 0, "test", "Test", stories, None, "")
        self.assertEqual(len(result), 2)

    def test_len_below_target_returns_all(self):
        stories = [{"id": str(i)} for i in range(3)]
        result = _apply_target_count(None, None, 0, "test", "Test", stories, 10, "")
        self.assertEqual(len(result), 3)

    def test_len_equals_target_returns_all(self):
        stories = [{"id": str(i)} for i in range(5)]
        result = _apply_target_count(None, None, 0, "test", "Test", stories, 5, "")
        self.assertEqual(len(result), 5)

    def test_len_above_target_uses_sorting_when_small(self):
        """When len <= target * 2, uses deterministic sort (not LLM)."""
        stories = [
            {"id": str(i), "significance": i, "novelty": i, "relevance_design": i}
            for i in range(6)  # 6 <= 3 * 2 = 6, so deterministic sort
        ]
        result = _apply_target_count(None, None, 0, "test", "Test", stories, 3, "")
        self.assertEqual(len(result), 3)
        # Should be sorted by significance desc, so highest first
        self.assertEqual(result[0]["significance"], 5)
        self.assertEqual(result[1]["significance"], 4)
        self.assertEqual(result[2]["significance"], 3)

    def test_len_above_target_uses_sorting_novelty_tiebreak(self):
        """When significance ties, novelty is the tiebreaker."""
        stories = [
            {"id": "a", "significance": 5, "novelty": 1},
            {"id": "b", "significance": 5, "novelty": 3},
            {"id": "c", "significance": 5, "novelty": 2},
        ]
        result = _apply_target_count(None, None, 0, "test", "Test", stories, 2, "")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "b")  # highest novelty
        self.assertEqual(result[1]["id"], "c")  # second highest novelty

    def test_len_above_target_uses_sorting_relevance_tiebreak(self):
        """When significance and novelty tie, relevance_design is the tiebreaker."""
        stories = [
            {"id": "a", "significance": 5, "novelty": 3, "relevance_design": 1},
            {"id": "b", "significance": 5, "novelty": 3, "relevance_design": 2},
        ]
        result = _apply_target_count(None, None, 0, "test", "Test", stories, 1, "")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "b")  # highest relevance


if __name__ == "__main__":
    unittest.main()
