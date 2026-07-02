"""Pre-run self-check (doctor) tests.

No mocks. The doctor's only I/O seams (``tags_fetch``, ``probe``, ``sleep``) are
dependency-injected exactly like the fetchers' ``fetch=`` seam, so the real
check logic runs against committed fixtures / deterministic callables — never a
patched network or filesystem. Path and dep checks run against the real repo.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from pipeline.config import load_config
from pipeline.doctor import FAIL, OK, WARN, Check, DoctorReport, run_doctor

_TAGS = (Path(__file__).resolve().parent / "data" / "ollama_tags.json").read_text(
    encoding="utf-8"
)


def _cfg(**llm_over) -> dict:
    cfg = load_config()
    cfg.setdefault("llm", {}).update({"enabled": True, "model": "qwen3.6:35b"})
    cfg["llm"].update(llm_over)
    return cfg


def _nosleep(_seconds: float) -> None:
    return None


class ReportModel(unittest.TestCase):
    def test_status_and_ok(self) -> None:
        r = DoctorReport(checks=[Check("a", OK, "fine")])
        self.assertTrue(r.ok)
        self.assertEqual(r.status, "ok")
        r.checks.append(Check("b", WARN, "meh"))
        self.assertTrue(r.ok)
        self.assertEqual(r.status, "degraded")
        r.checks.append(Check("c", FAIL, "broken", "do x"))
        self.assertFalse(r.ok)
        self.assertEqual(r.status, "fail")

    def test_render_shows_hint_only_for_non_ok(self) -> None:
        r = DoctorReport(checks=[
            Check("ok-check", OK, "good", hint="ignored"),
            Check("bad-check", FAIL, "nope", hint="fix it"),
        ])
        text = r.render_text()
        self.assertIn("FAIL", text)
        self.assertIn("fix it", text)
        self.assertNotIn("ignored", text)


class OllamaCheck(unittest.TestCase):
    def test_model_present(self) -> None:
        report = run_doctor(
            _cfg(), tags_fetch=lambda url: _TAGS, check_sources=False,
        )
        names = {c.name: c for c in report.checks}
        self.assertEqual(names["Ollama"].level, OK)
        self.assertEqual(names["Ollama model"].level, OK)

    def test_model_missing_is_fail(self) -> None:
        report = run_doctor(
            _cfg(model="does-not-exist:70b"),
            tags_fetch=lambda url: _TAGS, check_sources=False,
        )
        names = {c.name: c for c in report.checks}
        self.assertEqual(names["Ollama"].level, OK)
        self.assertEqual(names["Ollama model"].level, FAIL)
        self.assertIn("ollama pull", names["Ollama model"].hint)
        self.assertFalse(report.ok)

    def test_unreachable_is_fail(self) -> None:
        def boom(url: str) -> str:
            raise ConnectionRefusedError("connection refused")

        report = run_doctor(_cfg(), tags_fetch=boom, check_sources=False)
        names = {c.name: c for c in report.checks}
        self.assertEqual(names["Ollama"].level, FAIL)
        self.assertFalse(report.ok)

    def test_skeleton_only_skips_ollama_and_deps(self) -> None:
        report = run_doctor(
            _cfg(), skeleton_only=True, tags_fetch=lambda url: "", check_sources=False,
        )
        names = {c.name: c for c in report.checks}
        self.assertEqual(names["Ollama"].level, OK)
        self.assertIn("skipped", names["Ollama"].detail)
        self.assertEqual(names["enrich deps"].level, OK)
        self.assertTrue(report.ok)


class PathsCheck(unittest.TestCase):
    def test_real_output_dirs_writable(self) -> None:
        report = run_doctor(
            _cfg(), tags_fetch=lambda url: _TAGS, check_sources=False,
        )
        paths = next(c for c in report.checks if c.name == "output paths")
        self.assertEqual(paths.level, OK)


class SourcesCheck(unittest.TestCase):
    def test_all_reachable_is_ok(self) -> None:
        report = run_doctor(
            _cfg(), tags_fetch=lambda url: _TAGS,
            probe=lambda url: True, sleep=_nosleep,
        )
        sources = next(c for c in report.checks if c.name == "sources")
        self.assertEqual(sources.level, OK)
        self.assertTrue(report.ok)  # unreachable sources never block

    def test_unreachable_source_warns_not_fails(self) -> None:
        report = run_doctor(
            _cfg(), tags_fetch=lambda url: _TAGS,
            probe=lambda url: False, sleep=_nosleep,
        )
        sources = next(c for c in report.checks if c.name == "sources")
        self.assertEqual(sources.level, WARN)
        self.assertTrue(report.ok)
        self.assertEqual(report.status, "degraded")

    def test_probe_retries_then_succeeds(self) -> None:
        calls: dict[str, int] = {}

        def flaky(url: str) -> bool:
            calls[url] = calls.get(url, 0) + 1
            return calls[url] >= 2  # fail first attempt, succeed on retry

        report = run_doctor(
            _cfg(), tags_fetch=lambda url: _TAGS, probe=flaky, sleep=_nosleep,
        )
        sources = next(c for c in report.checks if c.name == "sources")
        self.assertEqual(sources.level, OK)
        self.assertTrue(all(v >= 2 for v in calls.values()))


if __name__ == "__main__":
    unittest.main()
