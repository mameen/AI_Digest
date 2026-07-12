"""Tests for crawl-driven leaderboard parsing.

Runs against the real (trimmed) AA crawl markdown committed under
``tests/data`` and the real constants in ``template.html`` — no mocks.
"""

from __future__ import annotations

import re
import unittest

from lib.paths import REPO_ROOT
from llm_pipeline.paths import VENDOR_DIR
from llm_pipeline.leaderboards import (
    _match_bracket,
    aa_rows,
    apply_crawl_leaderboards,
    arena_image_rows,
    parse_aa_models_md,
    parse_arena_image_md,
)

ROOT = REPO_ROOT
DATA = ROOT / "tests" / "data"
CRAWL_MD = DATA / "artificialanalysis.ai_leaderboards_models.md"
ARENA_T2I_MD = DATA / "arena.ai_leaderboard_text-to-image.md"
TEMPLATE = VENDOR_DIR / "template.html"

AA_COLS = ["#", "Model", "Provider", "Intelligence", "Speed (t/s)", "Latency (s)", "Context", "Price /1M"]
ARENA_IMAGE_COLS = ["#", "Model", "Provider", "Score", "Votes"]


def _extract_block(html: str, marker: str) -> str:
    start = html.index(marker) + len(marker)
    open_idx = html.index("{", start)
    return html[open_idx : _match_bracket(html, open_idx, "{", "}") + 1]


def _provider_colors() -> set[str]:
    block = _extract_block(TEMPLATE.read_text(encoding="utf-8"), "const PROVIDER_COLORS = ")
    keys = re.findall(r"(?:'([^']+)'|([A-Za-z][\w\-]*))\s*:", block)
    return {a or b for a, b in keys}


class ParseAaModels(unittest.TestCase):
    def setUp(self) -> None:
        self.parsed = parse_aa_models_md(CRAWL_MD.read_text(encoding="utf-8"))

    def test_top_ranks_reflect_fresh_crawl(self) -> None:
        rows = aa_rows(self.parsed)
        self.assertEqual(rows[0][1], "Claude Fable 5 (with fallback)")
        self.assertEqual(rows[0][3], 60)
        self.assertEqual(rows[1][1], "Claude Opus 4.8 (max)")
        self.assertEqual(rows[1][3], 56)
        models = [r[1] for r in rows]
        self.assertIn("Claude Opus 4.7 (max)", models)

    def test_rows_match_aa_column_arity(self) -> None:
        for row in aa_rows(self.parsed):
            self.assertEqual(len(row), len(AA_COLS))

    def test_provider_cell_strips_image_markdown(self) -> None:
        providers = {r["provider"] for r in self.parsed}
        self.assertIn("Anthropic", providers)
        self.assertFalse(any("![" in p or "](" in p for p in providers))

    def test_intelligence_is_int_without_asterisk(self) -> None:
        for r in self.parsed:
            self.assertIsInstance(r["intelligence"], int)

    def test_dashes_normalised(self) -> None:
        # Claude Fable 5 has no speed/latency in the crawl ("--").
        self.assertEqual(aa_rows(self.parsed)[0][4], "\u2014")
        self.assertEqual(aa_rows(self.parsed)[0][5], "\u2014")

    def test_every_provider_has_a_color(self) -> None:
        colors = _provider_colors()
        missing = {r["provider"] for r in self.parsed[:20]} - colors
        self.assertFalse(missing, f"providers missing from PROVIDER_COLORS: {sorted(missing)}")


class ParseArenaImage(unittest.TestCase):
    def setUp(self) -> None:
        self.parsed = parse_arena_image_md(ARENA_T2I_MD.read_text(encoding="utf-8"))

    def test_missing_models_are_now_present(self) -> None:
        # The models the seed rows omitted: FLUX, Ideogram, Krea.
        models = {r["model"] for r in self.parsed}
        self.assertIn("flux-2-max", models)
        self.assertIn("ideogram-4.0-quality", models)
        self.assertIn("krea-2-medium", models)
        self.assertIn("krea-2-large", models)

    def test_provider_extracted_with_and_without_brand_word(self) -> None:
        by_model = {r["model"]: r for r in self.parsed}
        # Plain link cell (no leading brand word).
        self.assertEqual(by_model["gpt-image-2 (medium)"]["provider"], "OpenAI")
        # Leading brand word before the link.
        self.assertEqual(by_model["flux-2-max"]["provider"], "Black Forest Labs")
        self.assertEqual(by_model["krea-2-medium"]["provider"], "Krea")

    def test_web_search_tag_stripped_from_model(self) -> None:
        models = {r["model"] for r in self.parsed}
        self.assertIn("gemini-3.1-flash-image-preview (nano-banana-2)", models)
        self.assertFalse(any("[web-search]" in m for m in models))

    def test_score_is_int_without_uncertainty(self) -> None:
        for r in self.parsed:
            self.assertIsInstance(r["score"], int)

    def test_rows_match_arena_image_column_arity(self) -> None:
        for row in arena_image_rows(self.parsed):
            self.assertEqual(len(row), len(ARENA_IMAGE_COLS))

    def test_rows_ranked_by_score_descending(self) -> None:
        rows = arena_image_rows(self.parsed)
        scores = [r[3] for r in rows]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(rows[0][1], "gpt-image-2 (medium)")

    def test_arena_image_providers_have_colors(self) -> None:
        colors = _provider_colors()
        missing = {r["provider"] for r in self.parsed} - colors
        self.assertFalse(missing, f"providers missing from PROVIDER_COLORS: {sorted(missing)}")


class ApplyToBlock(unittest.TestCase):
    def setUp(self) -> None:
        self.block = _extract_block(TEMPLATE.read_text(encoding="utf-8"), "const leaderboards = ")

    def test_stale_block_is_overwritten(self) -> None:
        # Sanity: the shipped template is the stale one (no Opus 4.8 / Fable 5).
        self.assertNotIn("Claude Opus 4.8", self.block)
        out = apply_crawl_leaderboards(self.block, DATA, updated_label="Jun 30, 2026")
        self.assertIn("Claude Fable 5 (with fallback)", out)
        self.assertIn("Claude Opus 4.8 (max)", out)
        self.assertIn('updated: "Jun 30, 2026"', out)

    def test_result_stays_brace_balanced(self) -> None:
        out = apply_crawl_leaderboards(self.block, DATA, updated_label="Jun 30, 2026")
        self.assertEqual(_match_bracket(out, 0, "{", "}"), len(out) - 1)

    def test_other_tabs_are_preserved(self) -> None:
        out = apply_crawl_leaderboards(self.block, DATA)
        for key in ("vellum", "open", "arena_image", "arena_video", "links"):
            self.assertIn(key, out)

    def test_arena_image_tab_gains_missing_models(self) -> None:
        # Seed rows stop at flux-2-max; FLUX flex/dev and Krea are absent until injected.
        self.assertNotIn("krea-2-medium", self.block)
        out = apply_crawl_leaderboards(self.block, DATA, updated_label="Jun 30, 2026")
        self.assertIn("krea-2-medium", out)
        self.assertIn("flux-2-flex", out)
        self.assertIn("ideogram-4.0-quality", out)

    def test_missing_crawl_dir_is_a_noop(self) -> None:
        out = apply_crawl_leaderboards(self.block, DATA / "does-not-exist")
        self.assertEqual(out, self.block)


if __name__ == "__main__":
    unittest.main()
