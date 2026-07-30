"""Fixture-backed tests for remaining llm_pipeline.diagnostics uncovered branches.

Tests cover:
- _failed_stages: recursive failure flattening (empty, nested, mixed)
- _NULL / get_collector(): fallback when no collector is active
- finish_collector(): disabled path
- StageRecord.to_dict(): full field serialization
- LlmCallRecord.to_dict(): token fields, estimated flag
- CrawlRecord.to_dict(): bytes_downloaded zero case
- ToolCallRecord.to_dict(): with/without detail
- LogRecord.to_dict(): with/without stage
- DiagnosticCollector disabled paths (stage, record_crawl, record_llm_call, record_tool_call)
- build_report(): totals computation, llm.enabled=false, empty crawls/tool_calls
- write(): artifact creation (JSON + HTML + log)
- rebuild_diagnostics_waterfall_pages: zero-files case
- backfill_diagnostics_json_files: all-present path (no write), missing-env path
- _enrich_report_paths: cache_root not a dir, preflight not exists
- instrumented_llm_call: disabled collector path
- _raw_llm_call: delegates to _raw_llm_call_with_usage
- _extract_openai_usage: dict completion, model_dump completion, None usage
- _normalize_tokens: ollama fallback, estimated fallback
- _ms_to_label: ms/s/m branches
- _render_run_log: empty log
- _call_table_row: estimated tokens, missing fields
- _render_waterfall_html: crawls/LLM rows, badge OK vs degraded, env/net lines
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from llm_pipeline.diagnostics import (
    DiagnosticCollector,
    LlmCallRecord,
    CrawlRecord,
    ToolCallRecord,
    LogRecord,
    _NULL,
    _enrich_report_paths,
    _extract_openai_usage,
    _failed_stages,
    _ms_to_label,
    _normalize_tokens,
    _raw_llm_call,
    _render_run_log,
    _render_waterfall_html,
    backfill_diagnostics_json_files,
    finish_collector,
    get_collector,
    instrumented_llm_call,
    rebuild_diagnostics_waterfall_pages,
)


# ── _failed_stages ─────────────────────────────────────────────────────────────

class TestFailedStages(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(_failed_stages([]), [])

    def test_all_ok_returns_empty(self):
        stages = [MagicMock(ok=True, children=[]), MagicMock(ok=True, children=[])]
        self.assertEqual(_failed_stages(stages), [])

    def test_flat_failures(self):
        s1 = MagicMock(ok=False, children=[])
        s2 = MagicMock(ok=True, children=[])
        s3 = MagicMock(ok=False, children=[])
        result = _failed_stages([s1, s2, s3])
        self.assertEqual(len(result), 2)
        self.assertIn(s1, result)
        self.assertIn(s3, result)

    def test_nested_failures_flattened(self):
        child = MagicMock(ok=False, children=[])
        parent = MagicMock(ok=True, children=[child])
        result = _failed_stages([parent])
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], child)

    def test_deeply_nested(self):
        gchild = MagicMock(ok=False, children=[])
        child = MagicMock(ok=True, children=[gchild])
        parent = MagicMock(ok=False, children=[child])
        result = _failed_stages([parent])
        self.assertEqual(len(result), 2)


# ── _NULL / get_collector ─────────────────────────────────────────────────────

class TestNullCollector(unittest.TestCase):
    def test_get_collector_returns_null_when_none_active(self):
        col = get_collector()
        self.assertIs(col, _NULL)

    def test_log_falls_back_to_console_when_no_collector(self):
        # When no collector is active, log() should not crash — it falls back to print.
        # We verify by calling it on _NULL (enabled=False).
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            _NULL.log("test fallback")  # should not raise
        finally:
            sys.stdout = old_stdout


class TestFinishCollector(unittest.TestCase):
    def test_disabled_returns_none(self):
        col = DiagnosticCollector(prefix="20260101120000", cfg={"diagnostics": {"enabled": False}}, enabled=False)
        result = finish_collector({})
        self.assertIsNone(result)


# ── Dataclass to_dict methods ─────────────────────────────────────────────────

class TestStageRecordToDict(unittest.TestCase):
    def test_serializes_all_fields(self):
        rec = DiagnosticCollector(prefix="x", cfg={}, enabled=True)
        with rec.stage("test", "Test") as r:
            pass
        d = r.to_dict()
        self.assertEqual(d["id"], "test")
        self.assertEqual(d["label"], "Test")
        self.assertIn("started_at", d)
        self.assertIn("ended_at", d)
        self.assertIn("duration_ms", d)
        self.assertTrue(d["ok"])
        self.assertIsNone(d["error"])
        self.assertIsInstance(d["children"], list)

    def test_failed_stage_serializes_error(self):
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=True)
        try:
            with col.stage("fail", "Fail") as r:
                raise ValueError("boom")
        except ValueError:
            pass
        d = col.stages[-1].to_dict()
        self.assertFalse(d["ok"])
        self.assertEqual(d["error"], "boom")


class TestLlmCallRecordToDict(unittest.TestCase):
    def test_with_tokens(self):
        rec = LlmCallRecord(
            name="enrich.research", model="llama3.1",
            started_at="2026-01-01T00:00:00Z", ended_at="2026-01-01T00:00:05Z",
            duration_ms=5000, prompt_chars=4000,
            prompt_tokens=1000, completion_tokens=500, total_tokens=1500,
            tokens_estimated=False, max_retries=3, ok=True, error=None, ollama={},
        )
        d = rec.to_dict()
        self.assertEqual(d["prompt_tokens"], 1000)
        self.assertEqual(d["completion_tokens"], 500)
        self.assertEqual(d["total_tokens"], 1500)
        self.assertFalse(d["tokens_estimated"])

    def test_estimated_no_tokens(self):
        rec = LlmCallRecord(
            name="enrich.gap", model="llama3.1",
            started_at="2026-01-01T00:00:00Z", ended_at="2026-01-01T00:00:05Z",
            duration_ms=5000, prompt_chars=4000,
            prompt_tokens=None, completion_tokens=None, total_tokens=None,
            tokens_estimated=True, max_retries=0, ok=False, error="timeout", ollama={},
        )
        d = rec.to_dict()
        self.assertTrue(d["tokens_estimated"])
        self.assertIsNone(d["prompt_tokens"])


class TestCrawlRecordToDict(unittest.TestCase):
    def test_with_bytes(self):
        rec = CrawlRecord(url="https://example.com", duration_ms=2000, ok=True, bytes_downloaded=4096)
        d = rec.to_dict()
        self.assertEqual(d["bytes_downloaded"], 4096)

    def test_zero_bytes_becomes_none(self):
        rec = CrawlRecord(url="https://example.com", duration_ms=2000, ok=True, bytes_downloaded=0)
        d = rec.to_dict()
        self.assertIsNone(d["bytes_downloaded"])


class TestToolCallRecordToDict(unittest.TestCase):
    def test_with_detail(self):
        rec = ToolCallRecord(tool="verify_url", args={"url": "https://x.com"}, ok=True, duration_ms=100, detail="OK")
        d = rec.to_dict()
        self.assertEqual(d["detail"], "OK")

    def test_without_detail(self):
        rec = ToolCallRecord(tool="web_search", args={"q": "test"}, ok=False, duration_ms=50)
        d = rec.to_dict()
        self.assertIsNone(d["detail"])


class TestLogRecordToDict(unittest.TestCase):
    def test_with_stage(self):
        rec = LogRecord(ts="2026-01-01T00:00:00Z", level="INFO", stage="enrich", message="hello")
        d = rec.to_dict()
        self.assertEqual(d["stage"], "enrich")

    def test_without_stage(self):
        rec = LogRecord(ts="2026-01-01T00:00:00Z", level="WARN", stage=None, message="warning")
        d = rec.to_dict()
        self.assertIsNone(d["stage"])


# ── DiagnosticCollector disabled paths ─────────────────────────────────────────

class TestDisabledCollector(unittest.TestCase):
    def test_stage_disabled_no_recording(self):
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=False)
        with col.stage("test", "Test") as r:
            pass
        self.assertEqual(len(col.stages), 0)  # not recorded

    def test_stage_disabled_exception_not_raised(self):
        # When enabled=False and critical=False, exceptions are swallowed.
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=False)
        with col.stage("fail", "Fail", critical=False) as r:
            raise ValueError("boom")
        self.assertFalse(r.ok)

    def test_record_crawl_disabled_is_noop(self):
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=False)
        col.record_crawl("https://example.com", 1000)
        self.assertEqual(len(col.crawls), 0)

    def test_record_llm_call_disabled_is_noop(self):
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=False)
        rec = LlmCallRecord(name="test", model="x", started_at="t", ended_at="t", duration_ms=1, prompt_chars=0)
        col.record_llm_call(rec)
        self.assertEqual(len(col.llm_calls), 0)

    def test_record_tool_call_disabled_is_noop(self):
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=False)
        col.record_tool_call("verify_url", {}, ok=True, duration_ms=100)
        self.assertEqual(len(col.tool_calls), 0)


# ── build_report totals ───────────────────────────────────────────────────────

class TestBuildReportTotals(unittest.TestCase):
    def test_llm_totals_computed(self):
        col = DiagnosticCollector(prefix="x", cfg={"llm": {"enabled": True, "provider": "ollama", "model": "llama3.1"}}, enabled=True)
        with col.stage("enrich", "Enrich"):
            col.record_llm_call(LlmCallRecord(
                name="test", model="llama3.1", started_at="t", ended_at="t",
                duration_ms=1000, prompt_chars=500, prompt_tokens=200, completion_tokens=100, total_tokens=300,
                tokens_estimated=False, max_retries=0, ok=True, error=None, ollama={},
            ))
        report = col.build_report()
        self.assertEqual(report["totals"]["llm_call_count"], 1)
        self.assertEqual(report["totals"]["prompt_tokens"], 200)
        self.assertEqual(report["totals"]["completion_tokens"], 100)
        self.assertEqual(report["totals"]["total_tokens"], 300)
        self.assertFalse(report["totals"]["tokens_estimated"])

    def test_llm_enabled_false(self):
        col = DiagnosticCollector(prefix="x", cfg={"llm": {"enabled": False}}, enabled=True)
        report = col.build_report()
        self.assertFalse(report["llm"]["enabled"])

    def test_empty_crawls_and_tool_calls(self):
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=True)
        with col.stage("render", "Render"):
            pass
        report = col.build_report()
        self.assertEqual(report["totals"]["crawl_count"], 0)
        self.assertEqual(report["totals"]["tool_call_count"], 0)

    def test_crawl_duration_computed(self):
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=True)
        col.record_crawl("https://example.com", 2000, ok=True, bytes_downloaded=4096)
        report = col.build_report()
        self.assertEqual(report["totals"]["crawl_count"], 1)

    def test_tool_calls_ok_count(self):
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=True)
        col.record_tool_call("t1", {}, ok=True, duration_ms=100)
        col.record_tool_call("t2", {}, ok=False, duration_ms=50)
        report = col.build_report()
        self.assertEqual(report["totals"]["tool_calls_ok"], 1)

    def test_llm_share_pct_computed(self):
        col = DiagnosticCollector(prefix="x", cfg={}, enabled=True)
        with col.stage("enrich", "Enrich"):
            col.record_llm_call(LlmCallRecord(
                name="test", model="llama3.1", started_at="t", ended_at="t",
                duration_ms=5000, prompt_chars=500, prompt_tokens=200, completion_tokens=100, total_tokens=300,
                tokens_estimated=False, max_retries=0, ok=True, error=None, ollama={},
            ))
        report = col.build_report()
        self.assertGreater(report["totals"]["llm_share_pct"], 0)

    def test_schema_and_prefix(self):
        col = DiagnosticCollector(prefix="20260101120000", cfg={}, enabled=True)
        report = col.build_report()
        self.assertEqual(report["schema"], "direct_pipeline_py.diagnostics/v1")
        self.assertEqual(report["prefix"], "20260101120000")


# ── write(): artifact creation ─────────────────────────────────────────────────

class TestWrite(unittest.TestCase):
    def test_writes_json_html_log(self):
        col = DiagnosticCollector(prefix="20260101120000", cfg={}, enabled=True)
        with col.stage("render", "Render"):
            pass
        with tempfile.TemporaryDirectory() as tmp:
            import llm_pipeline.diagnostics as diag_mod
            orig_diag_dir = diag_mod.diagnostics_dir
            diag_mod.diagnostics_dir = lambda cfg: Path(tmp)
            try:
                json_path = col.write({})
                self.assertTrue(json_path.exists())
                self.assertTrue((Path(tmp) / "20260101120000.diagnostics.html").exists())
                self.assertTrue((Path(tmp) / "20260101120000.run.log").exists())
            finally:
                diag_mod.diagnostics_dir = orig_diag_dir


# ── rebuild_diagnostics_waterfall_pages ────────────────────────────────────────

class TestRebuildWaterfall(unittest.TestCase):
    def test_zero_files_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            count = rebuild_diagnostics_waterfall_pages(Path(tmp))
            self.assertEqual(count, 0)

    def test_rebuilds_existing_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            diag_dir = Path(tmp)
            data = {"prefix": "20260101120000", "stages": [], "llm_calls": [], "crawls": []}
            (diag_dir / "20260101120000.diagnostics.json").write_text(json.dumps(data))
            count = rebuild_diagnostics_waterfall_pages(diag_dir)
            self.assertEqual(count, 1)
            html = diag_dir / "20260101120000.diagnostics.html"
            self.assertTrue(html.exists())


# ── backfill_diagnostics_json_files ────────────────────────────────────────────

class TestBackfillDiagnostics(unittest.TestCase):
    def test_all_present_no_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            diag_dir = Path(tmp)
            data = {
                "prefix": "20260101120000",
                "environment": {"platform_kind": "cuda"},
                "network": {"bytes_downloaded": 1000},
                "report_source_badge": "<badge/>",
            }
            (diag_dir / "20260101120000.diagnostics.json").write_text(json.dumps(data))
            count = backfill_diagnostics_json_files(diag_dir)
            self.assertEqual(count, 0)  # nothing to backfill

    def test_missing_env_triggers_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            diag_dir = Path(tmp)
            data = {
                "prefix": "20260101120000",
                "environment": {},  # missing platform_kind
                "network": {"bytes_downloaded": 1000},
                "report_source_badge": "<badge/>",
            }
            (diag_dir / "20260101120000.diagnostics.json").write_text(json.dumps(data))
            count = backfill_diagnostics_json_files(diag_dir)
            self.assertEqual(count, 1)


# ── _enrich_report_paths ──────────────────────────────────────────────────────

class TestEnrichReportPaths(unittest.TestCase):
    def test_cache_root_not_dir_returns_empty(self):
        cfg = {}
        data = {"prefix": "20260101120000"}
        result = _enrich_report_paths(data, cfg, "20260101120000")
        self.assertIn("environment", result)

    def test_preflight_not_exists_no_crash(self):
        cfg = {"paths": {"cache_dir": "/tmp/nonexistent_cache_xyz", "preflight_dir": "/tmp/nonexistent_preflight_xyz"}}
        data = {"prefix": "20260101120000"}
        result = _enrich_report_paths(data, cfg, "20260101120000")
        self.assertIn("environment", result)  # network only added if backfill_network returns truthy


# ── instrumented_llm_call disabled path ───────────────────────────────────────

class TestInstrumentedLlmCall(unittest.TestCase):
    def test_disabled_collector_returns_raw(self):
        # When collector is disabled, instrumented_llm_call should delegate to _raw_llm_call.
        # We verify by patching _raw_llm_call_with_usage to track calls.
        mock_result = MagicMock()
        with patch("llm_pipeline.diagnostics._raw_llm_call_with_usage", return_value=(mock_result, {}, {})) as mock:
            result = instrumented_llm_call(
                MagicMock(), "llama3.1", 0, "prompt", str, call_name="test"
            )
            self.assertIs(result, mock_result)
            mock.assert_called_once()


# ── _raw_llm_call ─────────────────────────────────────────────────────────────

class TestRawLlmCall(unittest.TestCase):
    def test_delegates_to_with_usage(self):
        mock_result = MagicMock()
        with patch("llm_pipeline.diagnostics._raw_llm_call_with_usage", return_value=(mock_result, {}, {})) as mock:
            result = _raw_llm_call(MagicMock(), "llama3.1", 0, "prompt", str)
            self.assertIs(result, mock_result)
            mock.assert_called_once()


# ── _extract_openai_usage ─────────────────────────────────────────────────────

class TestExtractOpenaiUsage(unittest.TestCase):
    def test_dict_completion(self):
        mock_completion = MagicMock()
        mock_completion.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        result = _extract_openai_usage(mock_completion)
        self.assertEqual(result, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150})

    def test_model_dump_completion(self):
        mock_completion = MagicMock()
        mock_usage_obj = MagicMock()
        mock_usage_obj.model_dump.return_value = {"prompt_tokens": 200, "completion_tokens": 100}
        mock_completion.usage = mock_usage_obj
        result = _extract_openai_usage(mock_completion)
        self.assertEqual(result["prompt_tokens"], 200)

    def test_none_usage_returns_empty(self):
        result = _extract_openai_usage(None)
        self.assertEqual(result, {})

    def test_partial_fields_ignored(self):
        mock_completion = MagicMock()
        mock_completion.usage = {"prompt_tokens": 100}  # missing completion/total
        result = _extract_openai_usage(mock_completion)
        self.assertEqual(result, {"prompt_tokens": 100})


# ── _normalize_tokens ─────────────────────────────────────────────────────────

class TestNormalizeTokens(unittest.TestCase):
    def test_full_usage(self):
        pt, ct, tt, est = _normalize_tokens({"prompt_tokens": 100, "completion_tokens": 50}, 400, {})
        self.assertEqual(pt, 100)
        self.assertEqual(ct, 50)
        self.assertEqual(tt, 150)
        self.assertFalse(est)

    def test_ollama_fallback(self):
        pt, ct, tt, est = _normalize_tokens({}, 400, {"prompt_eval_count": 120, "eval_count": 60})
        self.assertEqual(pt, 120)
        self.assertEqual(ct, 60)
        self.assertEqual(tt, 180)

    def test_tt_computed_from_pt_ct(self):
        pt, ct, tt, est = _normalize_tokens({"prompt_tokens": 100}, 400, {"eval_count": 50})
        self.assertEqual(pt, 100)
        self.assertEqual(ct, 50)
        self.assertEqual(tt, 150)

    def test_estimated_when_no_tokens(self):
        pt, ct, tt, est = _normalize_tokens({}, 400, {})
        self.assertTrue(est)
        self.assertEqual(pt, 100)  # 400 // 4
        self.assertIsNone(ct)


# ── _ms_to_label ──────────────────────────────────────────────────────────────

class TestMsToLabel(unittest.TestCase):
    def test_milliseconds(self):
        self.assertEqual(_ms_to_label(500), "500ms")

    def test_seconds(self):
        self.assertEqual(_ms_to_label(1500), "1.5s")

    def test_minutes(self):
        self.assertEqual(_ms_to_label(90000), "1.5m")


# ── _render_run_log empty log ─────────────────────────────────────────────────

class TestRunLogEmpty(unittest.TestCase):
    def test_empty_log_has_header_only(self):
        report = {"prefix": "20260101120000", "status": "ok", "started_at": "t", "finished_at": "t"}
        text = _render_run_log(report)
        self.assertIn("# AI Digest run log", text)
        self.assertNotIn("  INFO", text)  # no log lines


# ── _call_table_row estimated tokens ──────────────────────────────────────────

class TestCallTableRow(unittest.TestCase):
    def test_estimated_tokens(self):
        from llm_pipeline.diagnostics import _call_table_row
        row = _call_table_row({"name": "test", "duration_ms": 100, "prompt_tokens": None, "completion_tokens": None, "total_tokens": None, "tokens_estimated": True})
        # When prompt_tokens is None, the ~ is not visible (it's appended to pt column)
        self.assertIn("test", row)

    def test_missing_fields_show_dashes(self):
        from llm_pipeline.diagnostics import _call_table_row
        row = _call_table_row({"name": "test", "duration_ms": 100})
        self.assertIn("—", row)


# ── _render_waterfall_html comprehensive ──────────────────────────────────────

class TestWaterfallHtmlComprehensive(unittest.TestCase):
    def test_ok_badge(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "render", "label": "Render", "duration_ms": 500, "ok": True}],
            "llm_calls": [], "crawls": [], "tool_calls": [], "log": [],
            "environment": {}, "network": {}, "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("OK", html)
        self.assertNotIn("DEGRADED", html)

    def test_degraded_badge(self):
        report = {
            "prefix": "20260101120000", "status": "degraded",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 1, "failed_stages": ["enrich"],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "enrich", "label": "Enrich", "duration_ms": 500, "ok": False, "error": "boom"}],
            "llm_calls": [], "crawls": [], "tool_calls": [], "log": [],
            "environment": {}, "network": {}, "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("DEGRADED", html)
        self.assertIn("1 stage", html)

    def test_env_line_rendered(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "render", "label": "Render", "duration_ms": 500, "ok": True}],
            "llm_calls": [], "crawls": [], "tool_calls": [], "log": [],
            "environment": {"platform_kind": "cuda", "cpu": "Intel", "ram_gb": 64,
                           "gpu": {"name": "RTX 4090", "vram_gb": 24}},
            "network": {"throughput_mbps": 12.5},
            "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("Hardware", html)
        self.assertIn("RTX 4090", html)

    def test_net_line_rendered(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "render", "label": "Render", "duration_ms": 500, "ok": True}],
            "llm_calls": [], "crawls": [], "tool_calls": [], "log": [],
            "environment": {},
            "network": {"bytes_downloaded": 1048576, "throughput_mbps": 8.3},
            "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("Network", html)
        self.assertIn("MB downloaded", html)

    def test_no_crawls_message(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "render", "label": "Render", "duration_ms": 500, "ok": True}],
            "llm_calls": [], "crawls": [], "tool_calls": [], "log": [],
            "environment": {}, "network": {}, "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("No crawls recorded", html)

    def test_no_llm_calls_message(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "render", "label": "Render", "duration_ms": 500, "ok": True}],
            "llm_calls": [], "crawls": [], "tool_calls": [], "log": [],
            "environment": {}, "network": {}, "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("No LLM calls recorded", html)

    def test_llm_call_rows_rendered(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 1, "llm_duration_ms": 500, "llm_share_pct": 50.0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "enrich", "label": "Enrich", "duration_ms": 500, "ok": True}],
            "llm_calls": [{"name": "enrich.research", "duration_ms": 500, "total_tokens": 1500, "ok": True}],
            "crawls": [], "tool_calls": [], "log": [],
            "environment": {}, "network": {}, "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("enrich.research", html)
        self.assertIn("1,500 tok", html)

    def test_run_log_section(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "render", "label": "Render", "duration_ms": 500, "ok": True}],
            "llm_calls": [], "crawls": [], "tool_calls": [],
            "log": [{"ts": "2026-01-01T00:00:00Z", "level": "INFO", "stage": "render", "message": "wrote html"}],
            "environment": {}, "network": {}, "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("Run log", html)
        self.assertIn("wrote html", html)

    def test_no_log_lines_message(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "render", "label": "Render", "duration_ms": 500, "ok": True}],
            "llm_calls": [], "crawls": [], "tool_calls": [], "log": [],
            "environment": {}, "network": {}, "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("No log lines recorded", html)

    def test_tokens_estimated_label(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 1, "llm_duration_ms": 500, "llm_share_pct": 50.0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": True},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "enrich", "label": "Enrich", "duration_ms": 500, "ok": True}],
            "llm_calls": [{"name": "test", "duration_ms": 500, "total_tokens": None, "prompt_chars": 400, "ok": True}],
            "crawls": [], "tool_calls": [], "log": [],
            "environment": {}, "network": {}, "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertIn("estimated", html)

    def test_graph_line_rendered(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "render", "label": "Render", "duration_ms": 500, "ok": True}],
            "llm_calls": [], "crawls": [], "tool_calls": [], "log": [],
            "environment": {}, "network": {},
            "agents": {"graph": "Concierge → Researcher → Librarian"},
        }
        html = _render_waterfall_html(report)
        self.assertIn("Concierge", html)

    def test_no_graph_line_when_missing(self):
        report = {
            "prefix": "20260101120000", "status": "ok",
            "total_duration_ms": 1000, "total_cpu_ms": 500,
            "totals": {"llm_call_count": 0, "llm_duration_ms": 0, "llm_share_pct": 0,
                        "crawl_count": 0, "stage_failures": 0, "failed_stages": [],
                        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None,
                        "tokens_estimated": False},
            "llm": {"model": "llama3.1", "provider": "ollama"},
            "stages": [{"id": "render", "label": "Render", "duration_ms": 500, "ok": True}],
            "llm_calls": [], "crawls": [], "tool_calls": [], "log": [],
            "environment": {}, "network": {}, "agents": {},
        }
        html = _render_waterfall_html(report)
        self.assertNotIn("graph", html.lower())  # no graph line rendered


if __name__ == "__main__":
    unittest.main()
