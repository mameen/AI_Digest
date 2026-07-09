"""Tests for agentic/hermes/tools/web.py (fork of llm_pipeline/tools.py)."""

from __future__ import annotations

import unittest
from pathlib import Path

from agentic.hermes.tools.web import parse_ddg_results, verify_url, web_search

_DATA = Path(__file__).parent / "data"
_DDG_FIXTURE = _DATA / "duckduckgo_html_results.html"
_NOT_FOUND_FIXTURE = _DATA / "figure_not_found.html"
_LIVE_FIXTURE = _DATA / "figure_live_article.html"


def _fetch_from(status_map: dict[str, int], body_map: dict[str, str] | None = None):
    body_map = body_map or {}

    def fetch(url: str, timeout: int) -> tuple[int | None, str, str]:
        return status_map.get(url), url, body_map.get(url, "")

    return fetch


def _serve(html_text: str):
    def fetch_html(query: str, timeout: int) -> str:
        return html_text

    return fetch_html


class AgenticVerifyUrl(unittest.TestCase):
    def test_live_url(self) -> None:
        url = "https://www.figure.ai/news/figure-03-bmw-humanoid"
        body = _LIVE_FIXTURE.read_text(encoding="utf-8")
        out = verify_url(url, fetch=_fetch_from({url: 200}, {url: body}))
        self.assertTrue(out["ok"])

    def test_soft_404(self) -> None:
        url = "https://www.figure.ai/news/does-not-exist"
        body = _NOT_FOUND_FIXTURE.read_text(encoding="utf-8")
        out = verify_url(url, fetch=_fetch_from({url: 200}, {url: body}))
        self.assertFalse(out["ok"])
        self.assertIn("soft-404", out.get("error", ""))


class AgenticWebSearch(unittest.TestCase):
    html: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.html = _DDG_FIXTURE.read_text(encoding="utf-8")

    def test_parse_fixture(self) -> None:
        rows = parse_ddg_results(self.html, limit=3)
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(all(r["url"].startswith("http") for r in rows))

    def test_web_search_via_fixture(self) -> None:
        out = web_search("figure 03 bmw", fetch_html=_serve(self.html), limit=3)
        self.assertGreaterEqual(len(out["results"]), 1)
        self.assertNotIn("error", out)


if __name__ == "__main__":
    unittest.main()
