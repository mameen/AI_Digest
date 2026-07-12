"""Hardware + network snapshot helpers."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from llm_pipeline.environment import (
    LEGACY_RTX4090_ENV,
    SCHEMA,
    backfill_environment,
    capture_environment,
    detect_platform_kind,
    enrich_diagnostics_report,
    hw_metric_cards,
    summarize_network,
)


class EnvironmentCapture(unittest.TestCase):
    def test_capture_has_schema_and_platform_kind(self) -> None:
        env = capture_environment()
        self.assertEqual(env["schema"], SCHEMA)
        self.assertIn(env["platform_kind"], {"cuda", "mac", "cpu", "unknown"})
        self.assertIn("cpu", env)
        self.assertIn("gpu", env)

    @patch("llm_pipeline.environment._detect_cuda_gpu", return_value={"name": "RTX 4090", "backend": "cuda", "vram_gb": 24.0})
    def test_detect_platform_kind_cuda(self, _mock: object) -> None:
        self.assertEqual(detect_platform_kind(), "cuda")

    def test_summarize_network_prefers_cache_bytes(self) -> None:
        tmp = Path(self._testMethodName)
        tmp.mkdir(exist_ok=True)
        try:
            f = tmp / "sample.json"
            f.write_text('{"ok": true}', encoding="utf-8")
            summary = summarize_network([], cache_root=tmp, ingest_duration_ms=1000)
            self.assertGreater(summary["bytes_downloaded"], 0)
            self.assertEqual(summary["duration_ms"], 1000.0)
            self.assertIsNotNone(summary["throughput_mbps"])
        finally:
            f.unlink(missing_ok=True)
            tmp.rmdir()

    def test_summarize_network_falls_back_to_crawl_bytes(self) -> None:
        crawls = [{"duration_ms": 500, "bytes_downloaded": 2048}]
        summary = summarize_network(crawls)
        self.assertEqual(summary["bytes_downloaded"], 2048)


class EnvironmentBackfill(unittest.TestCase):
    def test_backfill_environment_uses_rtx4090_when_missing(self) -> None:
        env = backfill_environment(None)
        self.assertTrue(env.get("inferred"))
        self.assertEqual(env["gpu"]["name"], LEGACY_RTX4090_ENV["gpu"]["name"])
        self.assertEqual(env["platform_kind"], "cuda")

    def test_backfill_environment_preserves_captured(self) -> None:
        captured = {"schema": SCHEMA, "platform_kind": "mac", "cpu": "Apple M3", "gpu": {"name": "M3 GPU"}}
        self.assertEqual(backfill_environment(captured), captured)

    def test_hw_metric_cards_marks_inferred_gpu(self) -> None:
        cards = dict(hw_metric_cards(LEGACY_RTX4090_ENV, {"throughput_mbps": 12.5}))
        self.assertIn("(est.)", cards["GPU"])
        self.assertEqual(cards["Net BW"], "12.5 Mbps")
        self.assertEqual(cards["CPU"], "—")

    def test_enrich_adds_environment_and_network(self) -> None:
        report = {
            "prefix": "20260101000000",
            "stages": [{"id": "ingestion.crawl4ai", "duration_ms": 2000}],
            "crawls": [{"duration_ms": 2000, "bytes_downloaded": 4096}],
        }
        enriched = enrich_diagnostics_report(report)
        self.assertEqual(enriched["environment"]["platform_kind"], "cuda")
        self.assertIn("network", enriched)
        self.assertGreater(enriched["network"]["bytes_downloaded"], 0)


class DiagnosticsEnvironment(unittest.TestCase):
    def test_build_report_includes_environment_and_network(self) -> None:
        from llm_pipeline.diagnostics import DiagnosticCollector

        col = DiagnosticCollector(prefix="20260702120000", cfg={}, enabled=True)
        with col.stage("ingestion.preflight", "Preflight"):
            col.record_crawl("https://example.com", 120.0, bytes_downloaded=1024)
        report = col.build_report()
        self.assertEqual(report["environment"]["schema"], SCHEMA)
        self.assertIn("network", report)
        self.assertIn("bytes_downloaded", report["network"])


if __name__ == "__main__":
    unittest.main()
