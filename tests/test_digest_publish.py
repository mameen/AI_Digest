"""Fixture-backed tests for post-GO assess / deploy / publish — no mocks."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERMES = ROOT / "agentic" / "hermes"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(HERMES) not in sys.path:
    sys.path.insert(0, str(HERMES))

_spec = importlib.util.spec_from_file_location("publish", HERMES / "tools" / "publish.py")
assert _spec and _spec.loader
publish = importlib.util.module_from_spec(_spec)
sys.modules["publish"] = publish
_spec.loader.exec_module(publish)

FIXTURE_PREFIX = "20260709051615"


class DigestPublishTest(unittest.TestCase):
    def test_assess_known_good_run(self) -> None:
        result = publish.assess_run(FIXTURE_PREFIX)
        self.assertIn(result["goodness"], ("pass", "warn"))
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["stats"]["total"], 55)
        self.assertGreater(result["stats"]["categories"].get("youtube", 0), 0)
        self.assertTrue(result["preview"]["report_local"].startswith("file://"))
        self.assertTrue(Path(result["paths"]["report_html"]).is_file())
        self.assertIn("open_hint_macos", result)
        self.assertIn("vs_baseline", result)

    def test_digest_stats_matches_fixture(self) -> None:
        path = HERMES / "reports" / f"{FIXTURE_PREFIX}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        stats = publish.digest_stats(data)
        self.assertGreaterEqual(stats["total"], 55)
        self.assertIn("youtube", stats["categories"])

    def test_deploy_dry_run(self) -> None:
        result = publish.deploy_to_app(FIXTURE_PREFIX, dry_run=True, force=True)
        self.assertTrue(result.get("ok"), result)
        self.assertTrue(result.get("dry_run"))
        self.assertEqual(result.get("prefix"), FIXTURE_PREFIX)

    def test_open_report_dry_run(self) -> None:
        result = publish.open_report(FIXTURE_PREFIX, dry_run=True)
        self.assertTrue(result.get("ok"))
        self.assertTrue(result.get("dry_run"))
        self.assertTrue(Path(str(result.get("path") or "")).is_file())
        self.assertIn("command", result)

    def test_open_report_bad_target(self) -> None:
        with self.assertRaises(ValueError):
            publish.open_report(FIXTURE_PREFIX, target="no_such")

    def test_publish_dry_run(self) -> None:
        result = publish.publish_run(FIXTURE_PREFIX, dry_run=True, force=True)
        self.assertTrue(result.get("ok"), result)
        self.assertTrue(result.get("dry_run"))
        self.assertIn("would_stage", result)
        self.assertFalse(result.get("would_push"))

    def test_missing_prefix_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            publish.assess_run("no_such_prefix_ever")


if __name__ == "__main__":
    unittest.main()
