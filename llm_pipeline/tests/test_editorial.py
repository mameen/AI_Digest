"""Fixture-backed tests for llm_pipeline.editorial — pure functions."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from llm_pipeline.editorial import (
    CANONICAL_ORDER,
    CATEGORY_CATALOG,
    GAP_CATEGORY_IDS,
    SKELETON_CATEGORY_IDS,
    DEFAULT_CATEGORY_TARGETS,
    build_ingestion_context,
    category_id,
    category_targets,
    extract_aisearch_description,
    extract_aisearch_meta,
    extract_youtube_category,
    format_youtube_ingestion_block,
    make_category,
    normalize_category_metadata,
    normalize_preflight_category,
    order_categories,
    skeleton_category_map,
    stories_for_prompt,
    strip_private_fields,
    target_for,
)


class TestCategoryCatalog(unittest.TestCase):
    """Test CATEGORY_CATALOG and CANONICAL_ORDER constants."""

    def test_all_12_categories_present(self):
        self.assertEqual(len(CANONICAL_ORDER), 12)
        for cid in CANONICAL_ORDER:
            self.assertIn(cid, CATEGORY_CATALOG)

    def test_skeleton_ids_are_subset(self):
        for sid in SKELETON_CATEGORY_IDS:
            self.assertIn(sid, CANONICAL_ORDER)

    def test_gap_ids_are_subset(self):
        for gid in GAP_CATEGORY_IDS:
            self.assertIn(gid, CANONICAL_ORDER)


class TestCategoryId(unittest.TestCase):
    """Test category_id: extracts id from cat dict."""

    def test_returns_id_when_present(self):
        self.assertEqual(category_id({"id": "research"}), "research")

    def test_falls_back_to_category_key(self):
        self.assertEqual(category_id({"category": "youtube"}), "youtube")

    def test_returns_none_for_empty_cat(self):
        self.assertIsNone(category_id({}))


class TestNormalizePreflightCategory(unittest.TestCase):
    """Test normalize_preflight_category: maps preflight → production shape."""

    def test_maps_id_and_sets_defaults(self):
        cat = {"id": "research", "stories": []}
        result = normalize_preflight_category(cat)
        self.assertEqual(result["id"], "research")
        self.assertEqual(result["label"], CATEGORY_CATALOG["research"]["label"])
        self.assertEqual(result["icon"], CATEGORY_CATALOG["research"]["icon"])

    def test_strips_private_fields(self):
        cat = {"_private": "hidden", "id": "research", "stories": []}
        result = normalize_preflight_category(cat)
        self.assertNotIn("_private", result)

    def test_empty_cat_returns_stripped(self):
        cat = {"stories": []}
        result = normalize_preflight_category(cat)
        # No id means strip_private_fields returns empty dict
        self.assertNotIn("id", result)


class TestStripPrivateFields(unittest.TestCase):
    """Test strip_private_fields: removes _prefixed and preflight meta keys."""

    def test_removes_underscored_keys(self):
        cat = {"_video_url": "https://example.com", "id": "research"}
        result = strip_private_fields(cat)
        self.assertNotIn("_video_url", result)
        self.assertEqual(result["id"], "research")

    def test_removes_preflight_meta_keys(self):
        cat = {"video_url": "https://example.com", "id": "research"}
        result = strip_private_fields(cat)
        self.assertNotIn("video_url", result)


class TestMakeCategory(unittest.TestCase):
    """Test make_category: creates category dict with catalog metadata."""

    def test_creates_category_with_catalog_meta(self):
        cat = make_category("research", [{"id": "1", "title": "A"}])
        self.assertEqual(cat["id"], "research")
        self.assertEqual(cat["label"], CATEGORY_CATALOG["research"]["label"])
        self.assertEqual(len(cat["stories"]), 1)

    def test_uses_default_for_unknown_category(self):
        cat = make_category("unknown-cat", [])
        self.assertEqual(cat["label"], "unknown-cat")
        self.assertEqual(cat["icon"], "📌")


class TestOrderCategories(unittest.TestCase):
    """Test order_categories: orders by CANONICAL_ORDER, appends extras."""

    def test_ordered_by_canonical(self):
        cats = [
            {"id": "research", "label": "R", "stories": []},
            {"id": "aisearch", "label": "A", "stories": []},
        ]
        result = order_categories(cats)
        self.assertEqual(result[0]["id"], "aisearch")  # aisearch comes before research
        self.assertEqual(result[1]["id"], "research")

    def test_appends_unknown_categories(self):
        cats = [
            {"id": "research", "label": "R", "stories": []},
            {"id": "unknown", "label": "U", "stories": []},
        ]
        result = order_categories(cats)
        self.assertEqual(result[-1]["id"], "unknown")  # unknown goes last


class TestNormalizeCategoryMetadata(unittest.TestCase):
    """Test normalize_category_metadata: forces canonical label/icon."""

    def test_forces_canonical_label(self):
        cat = {"id": "research", "label": "WRONG LABEL"}
        result = normalize_category_metadata(cat)
        self.assertEqual(result["label"], CATEGORY_CATALOG["research"]["label"])

    def test_preserves_other_fields(self):
        cat = {"id": "research", "custom": "value", "label": "WRONG"}
        result = normalize_category_metadata(cat)
        self.assertEqual(result["custom"], "value")


class TestExtractAisearchMeta(unittest.TestCase):
    """Test extract_aisearch_meta: pulls video URL/label from aisearch category."""

    def test_returns_none_when_no_aisearch(self):
        cats = [{"id": "research", "stories": []}]
        url, label = extract_aisearch_meta(cats)
        self.assertIsNone(url)
        self.assertIsNone(label)

    def test_extracts_url_from_video_url_field(self):
        cats = [
            {
                "id": "aisearch",
                "video_url": "https://example.com/video?t=120",
                "video_label": "Test Video",
            }
        ]
        url, label = extract_aisearch_meta(cats)
        self.assertEqual(url, "https://example.com/video?t=120")  # full URL preserved
        self.assertEqual(label, "Test Video")

    def test_falls_back_to_first_story_url(self):
        cats = [
            {
                "id": "aisearch",
                "stories": [{"url": "https://example.com/watch?t=60"}],
            }
        ]
        url, _ = extract_aisearch_meta(cats)
        self.assertEqual(url, "https://example.com/watch?t=60")  # full URL preserved


class TestExtractAisearchDescription(unittest.TestCase):
    """Test extract_aisearch_description: pulls video description."""

    def test_returns_none_when_no_aisearch(self):
        cats = [{"id": "research", "stories": []}]
        self.assertIsNone(extract_aisearch_description(cats))

    def test_returns_stripped_description(self):
        cats = [{"id": "aisearch", "video_description": "  A description  "}]
        self.assertEqual(extract_aisearch_description(cats), "A description")


class TestExtractYoutubeCategory(unittest.TestCase):
    """Test extract_youtube_category: finds youtube category."""

    def test_returns_youtube_cat(self):
        cats = [{"id": "research"}, {"id": "youtube", "sources": []}]
        result = extract_youtube_category(cats)
        self.assertEqual(result["id"], "youtube")

    def test_returns_none_when_absent(self):
        cats = [{"id": "research"}]
        self.assertIsNone(extract_youtube_category(cats))


class TestFormatYoutubeIngestionBlock(unittest.TestCase):
    """Test format_youtube_ingestion_block: formats YouTube sources."""

    def test_formats_sources(self):
        cat = {
            "sources": [
                {"channel_label": "Channel A", "video_title": "Video 1", "description": "Desc 1"},
            ]
        }
        result = format_youtube_ingestion_block(cat, max_chars=1000)
        self.assertIn("Channel A", result)
        self.assertIn("Video 1", result)

    def test_respects_max_chars(self):
        cat = {
            "sources": [
                {"channel_label": "A", "video_title": "T", "description": "D" * 100},
            ]
        }
        result = format_youtube_ingestion_block(cat, max_chars=50)
        self.assertLessEqual(len(result), 50)


class TestSkeletonCategoryMap(unittest.TestCase):
    """Test skeleton_category_map: maps skeleton categories by id."""

    def test_maps_categories(self):
        skeleton = {
            "categories": [
                {"id": "research", "stories": []},
                {"id": "aisearch", "stories": []},
            ]
        }
        result = skeleton_category_map(skeleton)
        self.assertIn("research", result)
        self.assertIn("aisearch", result)

    def test_empty_skeleton(self):
        result = skeleton_category_map({})
        self.assertEqual(result, {})


class TestStoriesForPrompt(unittest.TestCase):
    """Test stories_for_prompt: serializes stories to JSON."""

    def test_serializes_stories(self):
        stories = [{"id": "1", "title": "A"}]
        result = stories_for_prompt(stories)
        self.assertIn('"id": "1"', result)

    def test_respects_limit(self):
        stories = [{"id": str(i)} for i in range(10)]
        result = stories_for_prompt(stories, limit=3)
        # Should contain only first 3 items
        self.assertIn('"id": "0"', result)
        self.assertNotIn('"id": "9"', result)


class TestCategoryTargets(unittest.TestCase):
    """Test category_targets: merges config targets with defaults."""

    def test_returns_defaults_when_no_config(self):
        result = category_targets({})
        for key in DEFAULT_CATEGORY_TARGETS:
            self.assertIn(key, result)

    def test_merges_custom_targets(self):
        cfg = {"enrich": {"category_targets": {"research": 10}}}
        result = category_targets(cfg)
        self.assertEqual(result["research"], 10)
        self.assertEqual(result["aisearch"], DEFAULT_CATEGORY_TARGETS["aisearch"])

    def test_none_target_preserved(self):
        cfg = {"enrich": {"category_targets": {"youtube": None}}}
        result = category_targets(cfg)
        self.assertIsNone(result["youtube"])


class TestTargetFor(unittest.TestCase):
    """Test target_for: gets target for a single category."""

    def test_returns_target(self):
        cfg = {"enrich": {"category_targets": {"research": 7}}}
        self.assertEqual(target_for(cfg, "research"), 7)

    def test_returns_none_when_not_set(self):
        cfg = {}
        self.assertIsNone(target_for(cfg, "nonexistent"))


class TestBuildIngestionContext(unittest.TestCase):
    """Test build_ingestion_context: assembles ingestion context string."""

    def test_empty_skeleton_produces_minimal_context(self):
        skeleton = {"categories": [], "requires_web_fetch": []}
        result = build_ingestion_context(skeleton, [])
        self.assertEqual(result, "")

    def test_includes_video_description(self):
        skeleton = {
            "categories": [{"id": "aisearch", "video_description": "A video desc"}],
            "requires_web_fetch": [],
        }
        result = build_ingestion_context(skeleton, [])
        self.assertIn("theAIsearch video description", result)

    def test_includes_crawl_files(self):
        crawl_file = MagicMock(spec=Path)
        crawl_file.name = "test.md"
        crawl_file.read_text.return_value = "Crawled content"
        skeleton = {"categories": [], "requires_web_fetch": []}
        result = build_ingestion_context(skeleton, [crawl_file])
        self.assertIn("Crawled content", result)


if __name__ == "__main__":
    unittest.main()
