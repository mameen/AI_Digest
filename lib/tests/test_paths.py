"""Shared path constants — no mocks."""

from __future__ import annotations

import unittest

from lib.paths import AGENTIC_ROOT, LLM_PIPELINE_ROOT, REPO_ROOT, WEB_ROOT


class RepoPaths(unittest.TestCase):
    def test_web_root_is_app(self) -> None:
        self.assertEqual(WEB_ROOT, REPO_ROOT / "app")

    def test_llm_pipeline_under_repo(self) -> None:
        self.assertTrue(str(LLM_PIPELINE_ROOT).startswith(str(REPO_ROOT)))
        self.assertTrue((LLM_PIPELINE_ROOT / "reports").is_dir())
        self.assertTrue((LLM_PIPELINE_ROOT / "vendor" / "ai-news-digest").is_dir())

    def test_agentic_root(self) -> None:
        self.assertTrue((AGENTIC_ROOT / "admin" / "manage.py").is_file())

    def test_admin_nav_hidden_by_default(self) -> None:
        from llm_pipeline.frame_nav import admin_nav_enabled, frame_nav_html

        self.assertFalse(admin_nav_enabled({"site": {}}))
        nav = frame_nav_html("reports", diagnostics_available=True, admin_available=False)
        self.assertNotIn("../admin/index.html", nav)
        self.assertNotIn("Control admin", nav)


if __name__ == "__main__":
    unittest.main()
