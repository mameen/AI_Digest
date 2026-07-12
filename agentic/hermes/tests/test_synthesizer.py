"""Tests for agentic synthesizer — librarian parse + LLM compose."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from lib.paths import REPO_ROOT

ROOT = REPO_ROOT
HERMES = ROOT / "agentic" / "hermes"
if str(HERMES) not in sys.path:
    sys.path.insert(0, str(HERMES))

_spec = importlib.util.spec_from_file_location(
    "synthesize", HERMES / "tools" / "synthesize.py"
)
assert _spec and _spec.loader
synthesize = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(synthesize)

EVAL_RUN_PREFIX = "eval" + "20260706201500"
EVAL_LIBRARIAN = (
    HERMES / ".runtime" / "artifacts" / EVAL_RUN_PREFIX / "librarian.md"
)
TABLE_LIBRARIAN = ROOT / "tests" / "data" / "agentic_librarian_knowledge_graph.md"
FULL_LIBRARIAN = (
    HERMES / ".runtime" / "artifacts" / "20260709120000" / "librarian.md"
)


class ParseLibrarianTest(unittest.TestCase):
    def test_parse_knowledge_graph_table_fixture(self) -> None:
        text = TABLE_LIBRARIAN.read_text(encoding="utf-8")
        entries = synthesize.parse_librarian_entries(text)
        self.assertGreaterEqual(len(entries), 9)
        urls = {e["url"] for e in entries}
        self.assertIn("https://artificialanalysis.ai/models/claude-fable-5", urls)
        self.assertIn("https://arxiv.org/abs/2607.06906", urls)
        self.assertIn("https://www.youtube.com/watch?v=SettwwX2cCI", urls)
        cats = {e["category_id"] for e in entries}
        self.assertIn("leaderboard", cats)
        self.assertIn("agentic-ai", cats)

    def test_parse_full_jul9_librarian_when_present(self) -> None:
        if not FULL_LIBRARIAN.is_file():
            self.skipTest("Jul 9 librarian runtime artifact missing")
        text = FULL_LIBRARIAN.read_text(encoding="utf-8")
        entries = synthesize.parse_librarian_entries(text)
        self.assertGreaterEqual(len(entries), 40, f"got {len(entries)} parsed entries")

    def test_parse_eval_fixture_entries(self) -> None:
        if not EVAL_LIBRARIAN.is_file():
            self.skipTest("eval librarian fixture missing — run eval GO first")
        text = EVAL_LIBRARIAN.read_text(encoding="utf-8")
        entries = synthesize.parse_librarian_entries(text)
        self.assertGreaterEqual(len(entries), 7)
        urls = [e["url"] for e in entries]
        self.assertTrue(any("artificialanalysis.ai" in u for u in urls))
        self.assertTrue(any("evalplus" in u or "swe-bench" in u.lower() for u in urls))
        cats = {e["category_id"] for e in entries}
        self.assertIn("leaderboard", cats)
        self.assertTrue(
            any(c in cats for c in ("research", "analytics")),
            f"expected eval frameworks in research or analytics, got {cats}",
        )


class SynthesizeDigestTest(unittest.TestCase):
    def test_synthesize_from_librarian_produces_valid_digest(self) -> None:
        if not EVAL_LIBRARIAN.is_file():
            self.skipTest("eval librarian fixture missing")
        from tools.baseline import agentic_llm_config
        from tools.artifacts import validate_synthesizer_artifact

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            text = EVAL_LIBRARIAN.read_text(encoding="utf-8")
            (ws / "librarian.md").write_text(text, encoding="utf-8")
            result = synthesize.synthesize_digest_from_librarian(
                ws,
                prefix=EVAL_RUN_PREFIX,
                cfg=agentic_llm_config(),
                librarian_text=text,
            )
            if not result.get("ok") and "unavailable" in str(result.get("error", "")).lower():
                self.skipTest(f"LLM unavailable: {result.get('error')}")
            self.assertTrue(result.get("ok"), result)
            self.assertEqual(validate_synthesizer_artifact(ws), [])


if __name__ == "__main__":
    unittest.main()
