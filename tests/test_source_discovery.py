#!/usr/bin/env python3
"""Tests for source_discovery skill discover.py script.

Tests verify:
- discover.py can read config/project.yaml source registry
- discover.py fetches items from RSS sources using rss_fetcher
- discover.py applies security_gate filtering
- discover.py outputs JSON with filtered items
- Exit code 0 on success, 1 on error
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import unittest

# Root of workspace
_REPO_ROOT = Path(__file__).parents[1]
_SKILLS_DIR = _REPO_ROOT / "agentic" / "kaggle_ai_agents"
_SRC = _SKILLS_DIR / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from kaggle_ai_agents.models import NewsItem


class TestSourceDiscoveryScript(unittest.TestCase):
    """Test discover.py script execution and output."""

    @classmethod
    def setUpClass(cls):
        """Verify discover.py exists and is executable."""
        cls.discover_script = (
            _SKILLS_DIR / "skills" / "source_discovery" / "scripts" / "discover.py"
        )
        cls.config_path = _SKILLS_DIR / "config" / "project.yaml"
        
        assert cls.discover_script.exists(), (
            f"discover.py not found at {cls.discover_script}"
        )
        assert cls.config_path.exists(), (
            f"project.yaml not found at {cls.config_path}"
        )

    def run_discover(self, config_path: Path | str, sources: list[str] | None = None) -> tuple[int, str]:
        """Run discover.py script and return (exit_code, stdout)."""
        cmd = [sys.executable, str(self.discover_script), "--config", str(config_path)]
        
        if sources:
            cmd.extend(["--sources"] + sources)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
        )
        return result.returncode, result.stdout

    def test_discover_with_default_config(self) -> None:
        """discover.py runs successfully with default config path."""
        exit_code, stdout = self.run_discover(self.config_path)
        self.assertEqual(exit_code, 0, f"stderr: {stdout}")
        
        # Output should be valid JSON
        items = json.loads(stdout)
        self.assertIsInstance(items, list)

    def test_discover_output_is_json_array(self) -> None:
        """discover.py outputs a JSON array of items."""
        exit_code, stdout = self.run_discover(self.config_path, sources=["openai-blog"])
        self.assertEqual(exit_code, 0)
        
        items = json.loads(stdout)
        self.assertIsInstance(items, list)

    def test_discover_items_have_required_fields(self) -> None:
        """Each item has source_id, title, url, summary."""
        exit_code, stdout = self.run_discover(self.config_path, sources=["openai-blog"])
        self.assertEqual(exit_code, 0)
        
        items = json.loads(stdout)
        required_fields = {"source_id", "title", "url", "summary"}
        
        for item in items:
            self.assertTrue(required_fields.issubset(item.keys()),
                          f"Item missing required fields: {item}")

    def test_discover_respects_source_filter(self) -> None:
        """discover.py respects --sources filter when provided."""
        exit_code, stdout = self.run_discover(
            self.config_path,
            sources=["openai-blog"]
        )
        self.assertEqual(exit_code, 0)
        
        items = json.loads(stdout)
        
        # All items should have source_id == "openai-blog"
        for item in items:
            self.assertEqual(item["source_id"], "openai-blog")

    def test_discover_filters_unsafe_content(self) -> None:
        """discover.py applies security_gate filter to block injections.
        
        This test verifies the mechanism works, but with real feeds
        we may not see blocked items. The security_gate tests verify
        the filter catches injections; this test verifies it's wired.
        """
        exit_code, stdout = self.run_discover(self.config_path, sources=["openai-blog"])
        self.assertEqual(exit_code, 0)
        
        # Parse output; if any items exist, they should be clean
        items = json.loads(stdout)
        for item in items:
            # URLs must be http/https (no javascript: or data:)
            self.assertTrue(
                item["url"].startswith(("http://", "https://")),
                f"URL scheme not http/https: {item['url']}"
            )

    def test_discover_empty_config(self) -> None:
        """discover.py handles config with no sources gracefully."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("project:\n  name: test\nsources: []\n")
            f.flush()
            
            try:
                exit_code, stdout = self.run_discover(f.name)
                self.assertEqual(exit_code, 0)
                items = json.loads(stdout)
                self.assertEqual(items, [])
            finally:
                Path(f.name).unlink()

    def test_discover_missing_config(self) -> None:
        """discover.py exits with 1 when config file not found."""
        exit_code, stdout = self.run_discover("/nonexistent/config.yaml")
        self.assertNotEqual(exit_code, 0)

    def test_discover_rss_sources_populated(self) -> None:
        """discover.py attempts to fetch items from RSS sources.
        
        Note: live feeds may timeout or fail; this test verifies the mechanism
        works (script runs, returns valid JSON). Fixture-backed tests in
        test_rss_fetcher.py verify parsing logic.
        """
        exit_code, stdout = self.run_discover(self.config_path, sources=["openai-blog"])
        self.assertEqual(exit_code, 0, "discover.py should exit 0 even if RSS fetch fails")
        
        items = json.loads(stdout)
        # Script runs successfully even if no items (e.g., network timeout)
        self.assertIsInstance(items, list)


if __name__ == "__main__":
    unittest.main()
