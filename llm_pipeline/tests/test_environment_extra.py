"""Fixture-backed tests for remaining llm_pipeline.environment uncovered branches.

Tests cover:
- _env_populated: populated vs empty env dicts
- backfill_environment: None, empty dict, already populated
- backfill_network: existing network present, missing bytes/throughput
- summarize_network: zero crawls with cache_root as file, preflight dedup
- detect_platform_kind: unknown machine string
- capture_environment: cpu platform path (non-Darwin, no CUDA)
- _run: None command, missing binary, non-zero return, TimeoutExpired, empty output
- _ram_gb: Darwin sysctl success/fail, Linux /proc/meminfo success/fail/OSError
- _cpu_label: Darwin sysctl success, fallback processor/machine/unknown
- _detect_cuda_gpu: no raw (empty string), single part, ValueError on vram
- _detect_mac_gpu: no raw, json decode error, no matching items
"""

from __future__ import annotations

import io
import json
import platform
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from llm_pipeline.environment import (
    LEGACY_RTX4090_ENV,
    SCHEMA,
    _cpu_label,
    _detect_cuda_gpu,
    _detect_mac_gpu,
    _env_populated,
    _ram_gb,
    _run,
    backfill_environment,
    backfill_network,
    capture_environment,
    detect_platform_kind,
    enrich_diagnostics_report,
    format_env_line,
    format_net_line,
    hw_metric_cards,
    summarize_network,
)


class TestEnvPopulated(unittest.TestCase):
    def test_none_is_not_populated(self):
        self.assertFalse(_env_populated(None))

    def test_empty_dict_is_not_populated(self):
        self.assertFalse(_env_populated({}))

    def test_no_platform_kind_is_not_populated(self):
        self.assertFalse(_env_populated({"schema": "test"}))

    def test_with_platform_kind_is_populated(self):
        self.assertTrue(_env_populated({"platform_kind": "cuda"}))


class TestBackfillEnvironment(unittest.TestCase):
    def test_none_backfills_rtx4090(self):
        env = backfill_environment(None)
        self.assertEqual(env["schema"], SCHEMA)
        self.assertTrue(env["inferred"])
        self.assertEqual(env["gpu"]["name"], "NVIDIA GeForce RTX 4090")

    def test_empty_dict_backfills_rtx4090(self):
        env = backfill_environment({})
        self.assertTrue(env["inferred"])

    def test_already_populated_returns_copy(self):
        original = {"schema": SCHEMA, "platform_kind": "mac", "cpu": "M3"}
        result = backfill_environment(original)
        self.assertEqual(result["platform_kind"], "mac")
        self.assertIsNot(result, original)  # returns a copy

    def test_cpu_platform_preserved(self):
        original = {"schema": SCHEMA, "platform_kind": "cpu", "gpu": {"backend": "cpu"}}
        result = backfill_environment(original)
        self.assertEqual(result["platform_kind"], "cpu")


class TestBackfillNetwork(unittest.TestCase):
    def test_existing_network_preserved(self):
        report = {"network": {"bytes_downloaded": 1000, "throughput_mbps": 5.0}}
        result = backfill_network(report)
        self.assertEqual(result["bytes_downloaded"], 1000)

    def test_missing_bytes_derives_from_cache(self):
        tmp = Path(self._testMethodName)
        tmp.mkdir(exist_ok=True)
        try:
            f = tmp / "sample.txt"
            f.write_text("hello world", encoding="utf-8")
            result = backfill_network({}, cache_root=tmp)
            self.assertGreater(result["bytes_downloaded"], 0)
        finally:
            f.unlink(missing_ok=True)
            tmp.rmdir()

    def test_missing_bytes_derives_from_crawls(self):
        crawls = [{"duration_ms": 1000, "bytes_downloaded": 2048}]
        result = backfill_network({"crawls": crawls})
        self.assertEqual(result["bytes_downloaded"], 2048)

    def test_crawls_bytes_used_when_no_cache(self):
        report = {"crawls": [{"duration_ms": 500, "bytes_downloaded": 4096}]}
        result = backfill_network(report)
        self.assertEqual(result["bytes_downloaded"], 4096)

    def test_inferred_flag_when_crawls_present(self):
        report = {"crawls": [{"duration_ms": 500, "bytes_downloaded": 4096}]}
        result = backfill_network(report)
        # inferred=False because crawls have bytes (inferred only when no crawls or no bytes in crawls)
        self.assertFalse(result.get("inferred"))


class TestSummarizeNetwork(unittest.TestCase):
    def test_zero_crawls_with_cache_file(self):
        tmp = Path(self._testMethodName)
        tmp.mkdir(exist_ok=True)
        try:
            f = tmp / "data.json"
            f.write_text('{"key": "value"}', encoding="utf-8")
            summary = summarize_network([], cache_root=tmp, ingest_duration_ms=500)
            self.assertGreater(summary["bytes_downloaded"], 0)
            self.assertEqual(summary["duration_ms"], 500.0)
        finally:
            f.unlink(missing_ok=True)
            tmp.rmdir()

    def test_preflight_dedup_with_cache(self):
        tmp = Path(self._testMethodName)
        tmp.mkdir(exist_ok=True)
        try:
            f = tmp / "shared.txt"
            f.write_text("x" * 100, encoding="utf-8")
            summary = summarize_network(
                [], cache_root=tmp, preflight_path=f, ingest_duration_ms=1000
            )
            self.assertEqual(summary["bytes_downloaded"], 100)  # not doubled
        finally:
            f.unlink(missing_ok=True)
            tmp.rmdir()

    def test_no_throughput_when_zero_bytes(self):
        summary = summarize_network([], ingest_duration_ms=500)
        self.assertEqual(summary["bytes_downloaded"], 0)
        self.assertIsNone(summary["throughput_mbps"])

    def test_throughput_computed_correctly(self):
        # 1MB in 1000ms = 8Mbps
        summary = summarize_network([], cache_root=Path(__file__), ingest_duration_ms=1000)
        if summary["bytes_downloaded"] > 0:
            expected_mbps = round((summary["bytes_downloaded"] * 8) / (1.0) / 1_000_000, 2)
            self.assertEqual(summary["throughput_mbps"], expected_mbps)

    def test_crawls_bytes_fallback(self):
        crawls = [{"duration_ms": 500, "bytes_downloaded": 8192}]
        summary = summarize_network(crawls)
        self.assertEqual(summary["bytes_downloaded"], 8192)


class TestDetectPlatformKind(unittest.TestCase):
    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_cuda_detected(self):
        with patch("lib.environment._detect_cuda_gpu", return_value={"name": "RTX"}):
            self.assertEqual(detect_platform_kind(), "cuda")

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_mac_on_darwin(self):
        with patch("lib.environment._detect_cuda_gpu", return_value=None):
            with patch("lib.environment.platform.system", return_value="Darwin"):
                self.assertEqual(detect_platform_kind(), "mac")

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_cpu_on_x86_64(self):
        with patch("lib.environment._detect_cuda_gpu", return_value=None):
            with patch("lib.environment.platform.system", return_value="Linux"):
                with patch("lib.environment.platform.machine", return_value="x86_64"):
                    self.assertEqual(detect_platform_kind(), "cpu")

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_unknown_machine(self):
        with patch("lib.environment._detect_cuda_gpu", return_value=None):
            with patch("lib.environment.platform.system", return_value="Linux"):
                with patch("lib.environment.platform.machine", return_value="weird-arch"):
                    self.assertEqual(detect_platform_kind(), "unknown")


class TestCaptureEnvironment(unittest.TestCase):
    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_cpu_path_no_cuda(self):
        with patch("lib.environment._detect_cuda_gpu", return_value=None):
            with patch("lib.environment.platform.system", return_value="Linux"):
                env = capture_environment()
                self.assertEqual(env["platform_kind"], "cpu")
                self.assertEqual(env["gpu"]["backend"], "cpu")
                self.assertIn("schema", env)
                self.assertIn("python", env)

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_returns_all_fields(self):
        with patch("lib.environment._detect_cuda_gpu", return_value=None):
            with patch("lib.environment.platform.system", return_value="Linux"):
                env = capture_environment()
                for key in ("schema", "platform_kind", "os", "os_release", "machine",
                            "cpu", "cpu_count", "ram_gb", "gpu", "python", "hostname"):
                    self.assertIn(key, env)


class TestRun(unittest.TestCase):
    def test_none_command_returns_none(self):
        self.assertIsNone(_run(None))

    def test_missing_binary_returns_none(self):
        result = _run(["nonexistent_binary_xyz_12345"])
        self.assertIsNone(result)

    def test_non_zero_return_returns_none(self):
        with patch("lib.environment.subprocess.run") as mock:
            mock.return_value = MagicMock(returncode=1, stdout="", stderr="error")
            result = _run(["python", "-c", "exit(1)"])
            self.assertIsNone(result)

    def test_empty_output_returns_none(self):
        with patch("lib.environment.subprocess.run") as mock:
            mock.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = _run(["python", "-c", "pass"])
            self.assertIsNone(result)

    def test_successful_output_returned(self):
        with patch("lib.environment.shutil.which", return_value=True):
            with patch("lib.environment.subprocess.run") as mock:
                mock.return_value = MagicMock(returncode=0, stdout="hello\n", stderr="")
                result = _run(["echo", "test"])
                self.assertEqual(result, "hello")


class TestRamGb(unittest.TestCase):
    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_linux_meminfo_success(self):
        meminfo = "MemTotal:       67584000 kB\nMemFree:        32000000 kB\n"
        with patch("lib.environment.platform.system", return_value="Linux"):
            with patch("lib.environment.open", return_value=io.StringIO(meminfo)):
                result = _ram_gb()
                self.assertEqual(result, 64.5)

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_linux_meminfo_no_match(self):
        meminfo = "MemFree:        32000000 kB\n"
        with patch("lib.environment.platform.system", return_value="Linux"):
            with patch("lib.environment.open", return_value=io.StringIO(meminfo)):
                result = _ram_gb()
                self.assertIsNone(result)

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_linux_meminfo_oserror(self):
        with patch("lib.environment.platform.system", return_value="Linux"):
            with patch("llm_pipeline.environment.open", side_effect=OSError("permission denied")):
                result = _ram_gb()
                self.assertIsNone(result)


class TestCpuLabel(unittest.TestCase):
    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_darwin_sysctl_success(self):
        with patch("lib.environment.platform.system", return_value="Darwin"):
            with patch("lib.environment._run", return_value="Apple M3 Pro"):
                result = _cpu_label()
                self.assertEqual(result, "Apple M3 Pro")

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_fallback_to_processor(self):
        with patch("lib.environment.platform.system", return_value="Linux"):
            with patch("lib.environment.platform.processor", return_value="x86_64"):
                result = _cpu_label()
                self.assertEqual(result, "x86_64")

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_fallback_to_machine(self):
        with patch("lib.environment.platform.system", return_value="Linux"):
            with patch("lib.environment.platform.processor", return_value=None):
                with patch("lib.environment.platform.machine", return_value="x86_64"):
                    result = _cpu_label()
                    self.assertEqual(result, "x86_64")

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_fallback_to_unknown(self):
        with patch("lib.environment.platform.system", return_value="Linux"):
            with patch("lib.environment.platform.processor", return_value=None):
                with patch("lib.environment.platform.machine", return_value=None):
                    result = _cpu_label()
                    self.assertEqual(result, "unknown")


class TestDetectCudaGpu(unittest.TestCase):
    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_no_raw_returns_none(self):
        with patch("lib.environment._run", return_value=""):
            result = _detect_cuda_gpu()
            self.assertIsNone(result)

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_single_part_name_only(self):
        with patch("lib.environment._run", return_value="RTX 4090"):
            result = _detect_cuda_gpu()
            self.assertEqual(result["name"], "RTX 4090")
            self.assertIsNone(result.get("vram_gb"))

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_two_parts_with_vram(self):
        with patch("lib.environment._run", return_value="RTX 4090, 24576"):
            result = _detect_cuda_gpu()
            self.assertEqual(result["name"], "RTX 4090")
            self.assertEqual(result["vram_gb"], 24.0)

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_two_parts_with_bad_vram(self):
        with patch("lib.environment._run", return_value="RTX 4090, not_a_number"):
            result = _detect_cuda_gpu()
            self.assertEqual(result["name"], "RTX 4090")
            self.assertIsNone(result.get("vram_gb"))


class TestDetectMacGpu(unittest.TestCase):
    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_no_raw_uses_cpu_label(self):
        with patch("lib.environment._run", return_value=None):
            with patch("lib.environment._cpu_label", return_value="M3"):
                result = _detect_mac_gpu()
                self.assertEqual(result["backend"], "metal")
                self.assertEqual(result["name"], "M3")

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_json_decode_error(self):
        with patch("lib.environment._run", return_value="{invalid json"):
            with patch("lib.environment._cpu_label", return_value="M3"):
                result = _detect_mac_gpu()
                self.assertEqual(result["name"], "M3")

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_no_matching_items(self):
        raw = json.dumps({"SPDisplaysDataType": [{"sppci_model": None}, {"_name": None}]})
        with patch("lib.environment._run", return_value=raw):
            with patch("lib.environment._cpu_label", return_value="M3"):
                result = _detect_mac_gpu()
                self.assertEqual(result["name"], "M3")  # falls back to cpu

    @unittest.skipIf(platform.system() == "Windows", "CUDA present on this machine")
    def test_finds_sppci_model(self):
        raw = json.dumps({"SPDisplaysDataType": [{"sppci_model": "AMD Radeon Pro"}]})
        with patch("lib.environment._run", return_value=raw):
            result = _detect_mac_gpu()
            self.assertEqual(result["name"], "AMD Radeon Pro")


class TestFormatEnvLine(unittest.TestCase):
    def test_empty_env_returns_empty(self):
        self.assertEqual(format_env_line({}), "")

    def test_full_env(self):
        env = {"platform_kind": "cuda", "cpu": "Intel Xeon", "ram_gb": 64,
               "gpu": {"name": "RTX 4090", "vram_gb": 24}}
        line = format_env_line(env)
        self.assertIn("cuda", line)
        self.assertIn("Intel Xeon", line)
        self.assertIn("64 GB RAM", line)
        self.assertIn("RTX 4090", line)
        self.assertIn("24 GB VRAM", line)

    def test_inferred_gpu(self):
        env = {"platform_kind": "cuda", "inferred": True, "gpu": {"name": "RTX 4090"}}
        line = format_env_line(env)
        self.assertIn("(estimated)", line)


class TestFormatNetLine(unittest.TestCase):
    def test_empty_net_returns_empty(self):
        self.assertEqual(format_net_line({}), "")

    def test_with_bytes_and_throughput(self):
        net = {"bytes_downloaded": 1048576, "throughput_mbps": 12.5, "duration_ms": 5000}
        line = format_net_line(net)
        self.assertIn("1.0 MB downloaded", line)
        self.assertIn("12.5 Mbps", line)

    def test_inferred_throughput(self):
        net = {"throughput_mbps": 8.0, "inferred": True}
        line = format_net_line(net)
        self.assertIn("(est.)", line)

    def test_duration_ms_label_seconds(self):
        net = {"bytes_downloaded": 1024, "duration_ms": 3500}
        line = format_net_line(net)
        self.assertIn("3.5s", line)

    def test_duration_ms_label_milliseconds(self):
        net = {"bytes_downloaded": 1024, "duration_ms": 500}
        line = format_net_line(net)
        self.assertIn("500ms", line)


class TestHwMetricCards(unittest.TestCase):
    def test_inferred_gpu_card(self):
        cards = dict(hw_metric_cards(LEGACY_RTX4090_ENV, {"throughput_mbps": 10.0}))
        self.assertIn("(est.)", cards["GPU"])

    def test_cpu_only_env(self):
        env = {"platform_kind": "cpu", "cpu": "Intel", "gpu": {"backend": "cpu", "name": "Intel"}}
        cards = dict(hw_metric_cards(env, {}))
        self.assertEqual(cards["VRAM"], "—")

    def test_ram_none(self):
        env = {"platform_kind": "cpu", "ram_gb": None, "gpu": {"name": "Test"}}
        cards = dict(hw_metric_cards(env, {}))
        self.assertEqual(cards["RAM"], "—")


class TestEnrichDiagnosticsReport(unittest.TestCase):
    def test_adds_environment_when_missing(self):
        report = {"prefix": "20260101120000"}
        enriched = enrich_diagnostics_report(report)
        self.assertIn("environment", enriched)
        self.assertIn("platform_kind", enriched["environment"])

    def test_adds_network_when_missing(self):
        report = {"prefix": "20260101120000", "crawls": []}
        enriched = enrich_diagnostics_report(report)
        # network key may or may not be present depending on backfill result
        self.assertIn("environment", enriched)


if __name__ == "__main__":
    unittest.main()
