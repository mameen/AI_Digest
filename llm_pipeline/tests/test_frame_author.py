"""Fixture-backed tests for llm_pipeline.frame_author — pure HTML generation."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from llm_pipeline.frame_author import (
    _author_photo_src,
    author_card_html,
    inject_author_card,
)


class TestAuthorPhotoSrc(unittest.TestCase):
    """Test _author_photo_src: resolves photo source from config."""

    def test_http_url_passed_through(self):
        cfg = {"site": {"author_photo_url": "https://example.com/photo.jpg"}}
        result = _author_photo_src(cfg, assets_prefix=None)
        self.assertEqual(result, "https://example.com/photo.jpg")

    def test_local_photo_uses_assets_prefix(self):
        cfg = {"site": {"author_photo": "ademiry.jpg"}}
        result = _author_photo_src(cfg, assets_prefix="../assets")
        self.assertEqual(result, "../assets/ademiry.jpg")

    def test_http_photo_url_passed_through(self):
        cfg = {"site": {"author_photo": "https://example.com/photo.jpg"}}
        result = _author_photo_src(cfg, assets_prefix=None)
        self.assertEqual(result, "https://example.com/photo.jpg")

    def test_no_photo_uses_default(self):
        cfg = {"site": {}}
        result = _author_photo_src(cfg, assets_prefix="../assets")
        self.assertEqual(result, "../assets/ademiry.jpg")  # defaults to ademiry.jpg


class TestAuthorCardHtml(unittest.TestCase):
    """Test author_card_html: generates correct HTML markup."""

    def test_generates_valid_author_card(self):
        cfg = {
            "site": {
                "author_name": "Test Author",
                "author_bio": "A bio.",
                "linkedin_url": "https://linkedin.com/in/test",
                "github_url": "https://github.com/test",
                "portfolio_url": "https://example.com",
            }
        }
        result = author_card_html(cfg, assets_prefix=None)
        self.assertIn('class="frame-author"', result)
        self.assertIn("Test Author", result)
        self.assertIn("A bio.", result)
        self.assertIn("LinkedIn", result)
        self.assertIn("GitHub", result)
        self.assertIn("Portfolio", result)

    def test_escapes_html_in_name(self):
        cfg = {
            "site": {
                "author_name": "<script>alert('xss')</script>",
                "author_bio": "A bio.",
            }
        }
        result = author_card_html(cfg, assets_prefix=None)
        self.assertIn("&lt;script&gt;", result)  # escaped

    def test_no_links_produces_empty_link_row(self):
        cfg = {"site": {"author_name": "No Links", "author_bio": "Bio"}}
        result = author_card_html(cfg, assets_prefix=None)
        self.assertNotIn("href=", result)

    def test_photo_present_when_url_provided(self):
        cfg = {
            "site": {
                "author_name": "Photo Author",
                "author_bio": "Bio",
                "author_photo_url": "https://example.com/photo.jpg",
            }
        }
        result = author_card_html(cfg, assets_prefix=None)
        self.assertIn('src="https://example.com/photo.jpg"', result)

    def test_no_photo_when_none_provided(self):
        cfg = {"site": {"author_name": "No Photo", "author_bio": "Bio"}}
        result = author_card_html(cfg, assets_prefix=None)
        self.assertNotIn("<img src=", result)


class TestInjectAuthorCard(unittest.TestCase):
    """Test inject_author_card: inserts author card into HTML."""

    def test_replaces_placeholder(self):
        html = "<div>__AUTHOR_CARD__</div>"
        cfg = {"site": {"author_name": "Test"}}
        result = inject_author_card(html, cfg)
        self.assertNotIn("__AUTHOR_CARD__", result)
        self.assertIn('class="frame-author"', result)

    def test_fallback_insert_before_details_close(self):
        html = "<div>\n</div>\n</details>"
        cfg = {"site": {"author_name": "Test"}}
        result = inject_author_card(html, cfg)
        self.assertIn('class="frame-author"', result)

    def test_noop_when_already_present(self):
        html = '<div class="frame-author">Already there</div>\n</details>'
        cfg = {"site": {"author_name": "Test"}}
        result = inject_author_card(html, cfg)
        self.assertEqual(result, html)  # unchanged


if __name__ == "__main__":
    unittest.main()
