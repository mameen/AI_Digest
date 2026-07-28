"""Tests for llm_pipeline.site_footer — footer HTML generation and injection."""

from __future__ import annotations

import unittest

from llm_pipeline.site_footer import (
    inject_site_footer,
    site_footer_css,
    site_footer_html,
)


class TestSiteFooterHtml(unittest.TestCase):
    """site_footer_html generates correct HTML with optional links."""

    def test_minimal_cfg(self):
        html = site_footer_html({})
        self.assertIn("AI Digest pipeline", html)
        self.assertIn("<footer class=\"site-footer\">", html)

    def test_author_short_used(self):
        html = site_footer_html({"site": {"author_short": "Test Author"}})
        self.assertIn("Test Author", html)

    def test_author_name_fallback(self):
        html = site_footer_html({"site": {"author_name": "Fallback Name"}})
        self.assertIn("Fallback Name", html)

    def test_linkedin_url_included(self):
        html = site_footer_html({"site": {"linkedin_url": "https://linkedin.com/in/test"}})
        self.assertIn('href="https://linkedin.com/in/test"', html)
        self.assertIn(">LinkedIn</a>", html)

    def test_portfolio_url_included(self):
        html = site_footer_html({"site": {"portfolio_url": "https://example.com"}})
        self.assertIn('href="https://example.com"', html)
        self.assertIn(">Portfolio</a>", html)

    def test_github_url_included(self):
        html = site_footer_html({"site": {"github_url": "https://github.com/test/repo"}})
        self.assertIn('href="https://github.com/test/repo"', html)
        self.assertIn(">GitHub</a>", html)

    def test_all_links_together(self):
        html = site_footer_html({
            "site": {
                "author_short": "Author",
                "linkedin_url": "https://li.in/test",
                "portfolio_url": "https://example.com",
                "github_url": "https://github.com/test/repo",
            }
        })
        self.assertIn("LinkedIn</a>", html)
        self.assertIn("Portfolio</a>", html)
        self.assertIn("GitHub</a>", html)

    def test_version_included(self):
        html = site_footer_html({})
        self.assertIn("site-footer-version", html)


class TestSiteFooterCss(unittest.TestCase):
    """site_footer_css returns non-empty CSS string."""

    def test_returns_string(self):
        css = site_footer_css()
        self.assertIsInstance(css, str)
        self.assertIn(".site-footer", css)

    def test_contains_link_styles(self):
        css = site_footer_css()
        self.assertIn("a:hover", css)


class TestInjectSiteFooter(unittest.TestCase):
    """inject_site_footer inserts footer before </body>."""

    def test_injects_when_missing(self):
        html = "<html><body>Hello</body></html>"
        result = inject_site_footer(html, {})
        self.assertIn("<footer class=\"site-footer\">", result)
        self.assertIn("</body>", result)

    def test_skips_when_already_present(self):
        html = "<html><body><footer class=\"site-footer\">Already</footer></body></html>"
        result = inject_site_footer(html, {})
        # Should not add a second footer
        count = result.count("<footer class=\"site-footer\">")
        self.assertEqual(count, 1)

    def test_skips_when_archive_frame_false(self):
        html = "<html><body>Hello</body></html>"
        result = inject_site_footer(html, {}, archive_frame=False)
        self.assertNotIn("site-footer", result)


if __name__ == "__main__":
    unittest.main()
