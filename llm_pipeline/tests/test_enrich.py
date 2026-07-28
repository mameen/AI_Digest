"""Fixture-backed tests for llm_pipeline.enrich — pure functions (no LLM).

Tests cover:
- _with_provenance: provenance stamping logic
- _prior_category_stories: grounded story extraction from prior digests
- _carry_forward_empty: carry-forward seeding for empty categories
- _promote_skeleton: skeleton promotion when llm.enabled=false
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Use lib.* imports (Track 2) — shims in llm_pipeline/ still work but emit warnings
from lib.schema import Category, Story

# Import the module under test
from llm_pipeline.enrich import (
    _carry_forward_empty,
    _prior_category_stories,
    _promote_skeleton,
    _with_provenance,
)


class TestWithProvenance(unittest.TestCase):
    """Test _with_provenance: stamps provenance on stories that lack it."""

    def test_stamps_missing_provenance(self):
        stories = [
            {"id": "1", "title": "A"},
            {"id": "2", "title": "B"},
        ]
        result = _with_provenance(stories, "skeleton:test")
        self.assertEqual(result[0]["provenance"], "skeleton:test")
        self.assertEqual(result[1]["provenance"], "skeleton:test")

    def test_preserves_existing_provenance(self):
        stories = [
            {"id": "1", "title": "A", "provenance": "crawl:existing"},
            {"id": "2", "title": "B"},
        ]
        result = _with_provenance(stories, "skeleton:test")
        self.assertEqual(result[0]["provenance"], "crawl:existing")  # preserved
        self.assertEqual(result[1]["provenance"], "skeleton:test")   # stamped

    def test_ignores_non_dict_entries(self):
        stories = [
            {"id": "1", "title": "A"},
            "not a dict",
            None,
        ]
        result = _with_provenance(stories, "skeleton:test")
        self.assertEqual(result[0]["provenance"], "skeleton:test")
        self.assertEqual(result[1], "not a dict")  # unchanged
        self.assertIsNone(result[2])  # unchanged

    def test_empty_list_returns_empty(self):
        result = _with_provenance([], "skeleton:test")
        self.assertEqual(result, [])


class TestPriorCategoryStories(unittest.TestCase):
    """Test _prior_category_stories: extracts grounded stories from prior digest."""

    def test_returns_only_url_bearing_stories(self):
        digest = {
            "categories": [
                {
                    "id": "research",
                    "stories": [
                        {"id": "1", "title": "A", "url": "https://example.com/1"},
                        {"id": "2", "title": "B"},  # no url
                        {"id": "3", "title": "C", "url": "https://example.com/3"},
                    ],
                }
            ]
        }
        result = _prior_category_stories(digest, "research")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "1")
        self.assertEqual(result[1]["id"], "3")

    def test_absent_category_is_empty(self):
        digest = {
            "categories": [
                {"id": "research", "stories": [{"id": "1", "title": "A"}]},
            ]
        }
        result = _prior_category_stories(digest, "nonexistent")
        self.assertEqual(result, [])

    def test_returns_deep_copies(self):
        digest = {
            "categories": [
                {"id": "research", "stories": [{"id": "1", "title": "A", "url": "https://example.com"}]},
            ]
        }
        result = _prior_category_stories(digest, "research")
        result[0]["title"] = "MODIFIED"
        # Original should be unchanged (deep copy)
        original_title = digest["categories"][0]["stories"][0]["title"]
        self.assertEqual(original_title, "A")


class TestCarryForwardEmpty(unittest.TestCase):
    """Test _carry_forward_empty: seeds empty categories from prior digests."""

    def test_no_prior_digests_is_noop(self):
        enriched = {"research": {"id": "research", "stories": []}}
        result = _carry_forward_empty(enriched, [], ["research"], {})
        self.assertEqual(result, [])
        self.assertEqual(enriched["research"]["stories"], [])

    def test_non_empty_category_is_untouched(self):
        enriched = {
            "research": {"id": "research", "stories": [{"id": "1", "title": "A"}]},
        }
        prior_digests = [
            {
                "filename_prefix": "20260727120000",
                "categories": [
                    {"id": "research", "stories": [{"id": "99", "title": "Prior", "url": "https://prior.com"}]},
                ],
            }
        ]
        result = _carry_forward_empty(enriched, prior_digests, ["research"], {})
        self.assertEqual(result, [])  # not seeded (already has stories)

    def test_bounded_to_target(self):
        enriched = {"research": {"id": "research", "stories": []}}
        prior_digests = [
            {
                "filename_prefix": "20260727120000",
                "categories": [
                    {
                        "id": "research",
                        "stories": [
                            {"id": f"{i}", "title": f"Story {i}", "url": f"https://example.com/{i}"}
                            for i in range(10)
                        ],
                    },
                ],
            }
        ]
        targets = {"research": 3}
        result = _carry_forward_empty(enriched, prior_digests, ["research"], targets)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "research")
        self.assertEqual(result[0][2], 3)  # seeded 3 stories
        self.assertEqual(len(enriched["research"]["stories"]), 3)

    def test_seeds_empty_required_from_most_recent(self):
        enriched = {"research": {"id": "research", "stories": []}}
        prior_digests = [
            {
                "filename_prefix": "20260726120000",
                "categories": [{"id": "research", "stories": []}],  # empty in older digest
            },
            {
                "filename_prefix": "20260727120000",
                "categories": [
                    {"id": "research", "stories": [{"id": "1", "title": "A", "url": "https://example.com"}]},
                ],
            },
        ]
        result = _carry_forward_empty(enriched, prior_digests, ["research"], {})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], "20260727120000")  # most recent wins

    def test_carried_stories_are_flagged(self):
        enriched = {"research": {"id": "research", "stories": []}}
        prior_digests = [
            {
                "filename_prefix": "20260727120000",
                "categories": [
                    {"id": "research", "stories": [{"id": "1", "title": "A", "url": "https://example.com"}]},
                ],
            }
        ]
        _carry_forward_empty(enriched, prior_digests, ["research"], {})
        story = enriched["research"]["stories"][0]
        self.assertTrue(story.get("carried_forward"))
        self.assertEqual(story.get("provenance"), "carry:20260727120000")


class TestPromoteSkeleton(unittest.TestCase):
    """Test _promote_skeleton: promotes preflight skeleton when llm.enabled=false."""

    def test_promotes_categories_as_is(self):
        window = MagicMock()
        window.generated_at = "2026-07-28T12:00:00Z"
        window.prefix = "20260728120000"
        window.label.return_value = "2026-07-18 -> 2026-07-28 (10d)"

        skeleton = {
            "summary": "Test digest",
            "categories": [
                {
                    "id": "research",
                    "label": "Research",
                    "icon": "🔬",
                    "stories": [
                        {"id": "1", "title": "A", "url": "https://example.com/1"},
                    ],
                }
            ],
        }

        result = _promote_skeleton(window, skeleton)

        self.assertEqual(result["filename_prefix"], "20260728120000")
        self.assertEqual(result["summary"], "Test digest")
        self.assertEqual(len(result["categories"]), 1)
        self.assertEqual(result["categories"][0]["id"], "research")
        self.assertEqual(len(result["categories"][0]["stories"]), 1)

    def test_empty_categories_produces_empty_list(self):
        window = MagicMock()
        window.generated_at = "2026-07-28T12:00:00Z"
        window.prefix = "20260728120000"
        window.label.return_value = "2026-07-18 -> 2026-07-28 (10d)"

        skeleton = {"summary": "Empty", "categories": []}
        result = _promote_skeleton(window, skeleton)

        self.assertEqual(result["categories"], [])


if __name__ == "__main__":
    unittest.main()
