"""Tests for agentic synthesizer — librarian parse + LLM compose."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERMES = ROOT / "agentic" / "hermes"
if str(HERMES) not in sys.path:
    sys.path.insert(0, str(HERMES))

_spec = importlib.util.spec_from_file_location(
    "synthesize", HERMES / "tools" / "synthesize.py"
)
assert _spec and _spec.loader
synthesize = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(synthesize)

EVAL_LIBRARIAN = (
    HERMES / ".runtime" / "artifacts" / "eval20260706201500" / "librarian.md"
)


class ParseLibrarianTest(unittest.TestCase):
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
                prefix="eval20260706201500",
                cfg=agentic_llm_config(),
                librarian_text=text,
            )
            if not result.get("ok") and "unavailable" in str(result.get("error", "")).lower():
                self.skipTest(f"LLM unavailable: {result.get('error')}")
            self.assertTrue(result.get("ok"), result)
            self.assertEqual(validate_synthesizer_artifact(ws), [])


if __name__ == "__main__":
    unittest.main()
