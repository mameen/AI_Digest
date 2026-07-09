"""Tests for structured-API leaderboard sources.

Runs against the real (trimmed) EvalPlus + SWE-bench JSON committed under
``tests/data`` and the real ``leaderboards`` object in ``template.html`` — no
mocks. Fixture filenames match the registry slugs so the injector can read them
directly.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from llm_pipeline.paths import VENDOR_DIR
from pipeline.leaderboards import _match_bracket
from pipeline.structured_sources import (
    apply_structured_leaderboards,
    evalplus_rows,
    swebench_rows,
)

TEMPLATE = VENDOR_DIR / "template.html"
DATA = Path(__file__).resolve().parent / "data"

EVALPLUS = json.loads((DATA / "evalplus_results.json").read_text(encoding="utf-8"))
SWEBENCH = json.loads((DATA / "swebench_leaderboards.json").read_text(encoding="utf-8"))


def _extract_block(html: str, marker: str) -> str:
    start = html.index(marker) + len(marker)
    open_idx = html.index("{", start)
    return html[open_idx : _match_bracket(html, open_idx, "{", "}") + 1]


class EvalPlusRows(unittest.TestCase):
    def test_ranked_by_humaneval_plus(self) -> None:
        rows = evalplus_rows(EVALPLUS, limit=5)
        # OpenCoder-8B-Instruct has the highest humaneval+ (77.4) in the fixture.
        self.assertEqual(rows[0][1], "OpenCoder-8B-Instruct")
        self.assertEqual(rows[0][3], 77.4)  # HumanEval+
        self.assertEqual(rows[0][4], 71.4)  # MBPP+
        self.assertEqual(rows[0][2], 8)     # size 8.0 -> int
        # Strictly non-increasing HumanEval+ down the table; ranks are 1..n.
        scores = [r[3] for r in rows]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([r[0] for r in rows], list(range(1, len(rows) + 1)))

    def test_missing_metrics_become_dash(self) -> None:
        rows = evalplus_rows(EVALPLUS, limit=12)
        # Code-13B has null mbpp+ in the fixture -> em-dash placeholder.
        code13b = next(r for r in rows if r[1] == "Code-13B")
        self.assertEqual(code13b[4], "—")


class SweBenchRows(unittest.TestCase):
    def test_verified_ranked_by_resolved(self) -> None:
        rows = swebench_rows(SWEBENCH, board="Verified", limit=8)
        self.assertTrue(rows[0][1].startswith("live-SWE-agent"))
        self.assertEqual(rows[0][2], 79.2)  # resolved %
        resolved = [r[2] for r in rows]
        self.assertEqual(resolved, sorted(resolved, reverse=True))

    def test_unknown_board_is_empty(self) -> None:
        self.assertEqual(swebench_rows(SWEBENCH, board="DoesNotExist"), [])


class ApplyToBlock(unittest.TestCase):
    def setUp(self) -> None:
        self.block = _extract_block(TEMPLATE.read_text(encoding="utf-8"), "const leaderboards = ")

    def test_seed_rows_overwritten_from_fixtures(self) -> None:
        # Sanity: the shipped seed has O1 Preview but not the fixture's OpenCoder.
        self.assertIn("O1 Preview (Sept 2024)", self.block)
        self.assertNotIn("OpenCoder-8B-Instruct", self.block)
        out = apply_structured_leaderboards(self.block, DATA, updated_label="Jun 30, 2026")
        self.assertIn("OpenCoder-8B-Instruct", out)        # EvalPlus tab refreshed
        self.assertIn("live-SWE-agent", out)               # SWE-bench tab refreshed
        self.assertIn('updated: "Jun 30, 2026"', out)

    def test_result_stays_brace_balanced(self) -> None:
        out = apply_structured_leaderboards(self.block, DATA, updated_label="Jun 30, 2026")
        self.assertEqual(_match_bracket(out, 0, "{", "}"), len(out) - 1)

    def test_missing_dir_is_noop(self) -> None:
        out = apply_structured_leaderboards(self.block, DATA / "does_not_exist")
        self.assertEqual(out, self.block)


if __name__ == "__main__":
    unittest.main()
