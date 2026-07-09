"""Run instrumentation: time, tokens, compute. JSON + waterfall HTML."""

from __future__ import annotations

import html
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from llm_pipeline.environment import (
    capture_environment,
    enrich_diagnostics_report,
    format_env_line,
    format_net_line,
    hw_metric_cards,
    summarize_network,
)
from llm_pipeline.paths import cache_dir, diagnostics_dir, preflight_dir
from llm_pipeline.site_footer import inject_site_footer
from llm_pipeline.diagnostics_frame import rebuild_diagnostics_archive


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _failed_stages(stages: list["StageRecord"]) -> list["StageRecord"]:
    """Flatten the stage tree to the records that failed (ok is False)."""
    out: list[StageRecord] = []
    for st in stages:
        if not st.ok:
            out.append(st)
        out.extend(_failed_stages(st.children))
    return out


# ── Active collector (set by run.py) ─────────────────────────────────────────

_active: DiagnosticCollector | None = None


def init_collector(prefix: str, cfg: dict[str, Any]) -> DiagnosticCollector:
    global _active
    dcfg = cfg.get("diagnostics") or {}
    enabled = bool(dcfg.get("enabled", True))
    _active = DiagnosticCollector(prefix=prefix, cfg=cfg, enabled=enabled)
    return _active


def get_collector() -> DiagnosticCollector:
    return _active or _NULL


def finish_collector(cfg: dict[str, Any]) -> Path | None:
    """Write diagnostics artifacts; return JSON path or None if disabled."""
    col = get_collector()
    if not col.enabled:
        return None
    return col.write(cfg)


def log(message: str, *, level: str = "INFO") -> None:
    """Route a milestone/warning through the active collector (buffer + console).

    Falls back to a plain console print when no collector is active, so it is
    always safe to call at any orchestration boundary.
    """
    get_collector().log(message, level=level)


# ── Data model ─────────────────────────────────────────────────────────────────


@dataclass
class StageRecord:
    id: str
    label: str
    started_at: str
    ended_at: str | None = None
    duration_ms: float = 0.0
    cpu_ms: float = 0.0
    ok: bool = True
    critical: bool = True
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    children: list[StageRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": round(self.duration_ms, 1),
            "cpu_ms": round(self.cpu_ms, 1),
            "ok": self.ok,
            "critical": self.critical,
            "error": self.error,
            "meta": self.meta,
            "children": [c.to_dict() for c in self.children],
        }


@dataclass
class LlmCallRecord:
    name: str
    model: str
    started_at: str
    ended_at: str
    duration_ms: float
    prompt_chars: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    tokens_estimated: bool = False
    max_retries: int = 0
    ok: bool = True
    error: str | None = None
    ollama: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": round(self.duration_ms, 1),
            "prompt_chars": self.prompt_chars,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "tokens_estimated": self.tokens_estimated,
            "max_retries": self.max_retries,
            "ok": self.ok,
            "error": self.error,
            "ollama": self.ollama,
        }


@dataclass
class CrawlRecord:
    url: str
    duration_ms: float
    ok: bool
    output_file: str | None = None
    error: str | None = None
    bytes_downloaded: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "duration_ms": round(self.duration_ms, 1),
            "ok": self.ok,
            "output_file": self.output_file,
            "error": self.error,
            "bytes_downloaded": self.bytes_downloaded or None,
        }


@dataclass
class ToolCallRecord:
    """One tool invocation from the grounding tool-loop (verify_url/web_search)."""

    tool: str
    args: dict[str, Any]
    ok: bool
    duration_ms: float
    detail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "args": self.args,
            "ok": self.ok,
            "duration_ms": round(self.duration_ms, 1),
            "detail": self.detail,
        }


@dataclass
class LogRecord:
    """One structured log line: timestamp, level, owning stage, message."""

    ts: str
    level: str
    stage: str | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"ts": self.ts, "level": self.level, "stage": self.stage, "message": self.message}


class DiagnosticCollector:
    def __init__(self, prefix: str, cfg: dict[str, Any], *, enabled: bool = True) -> None:
        self.prefix = prefix
        self.cfg = cfg
        self.enabled = enabled
        self.run_started_at = _utc_now()
        self._run_t0 = time.perf_counter()
        self._run_cpu0 = time.process_time()
        self.stages: list[StageRecord] = []
        self.llm_calls: list[LlmCallRecord] = []
        self.crawls: list[CrawlRecord] = []
        self.tool_calls: list[ToolCallRecord] = []
        self.logs: list[LogRecord] = []
        self._stack: list[StageRecord] = []
        self.environment = capture_environment() if enabled else {}

    def log(self, message: str, *, level: str = "INFO") -> None:
        """Record a structured log line and echo it to the console.

        Always prints (so runs stay observable even with diagnostics disabled);
        the timestamped, stage-tagged record is buffered only when enabled and
        is persisted into the diagnostics JSON, HTML and ``<prefix>.run.log``.
        """
        stage = self._stack[-1].id if self._stack else None
        level = level.upper()
        print(message if level == "INFO" else f"{level} {message}")
        if self.enabled:
            self.logs.append(
                LogRecord(ts=_utc_now(), level=level, stage=stage, message=message.strip())
            )

    @contextmanager
    def stage(
        self, stage_id: str, label: str, *, critical: bool = True, **meta: Any
    ) -> Iterator[StageRecord]:
        """Time a pipeline stage and capture its outcome.

        On exception the stage is recorded as failed. A ``critical`` stage
        re-raises (aborting the run); a non-critical stage swallows the error
        after recording it, so a single flaky source degrades the report rather
        than sinking the whole run. The failure is surfaced in diagnostics.
        """
        rec = StageRecord(
            id=stage_id, label=label, started_at=_utc_now(),
            critical=critical, meta=dict(meta),
        )
        if not self.enabled:
            try:
                yield rec
            except Exception as exc:  # noqa: BLE001
                rec.ok, rec.error = False, str(exc)
                if critical:
                    self.log(f"stage {stage_id} FAILED: {exc}", level="ERROR")
                    raise
                self.log(f"stage {stage_id} degraded (non-critical): {exc}", level="WARN")
            return

        parent = self._stack[-1] if self._stack else None
        if parent is not None:
            parent.children.append(rec)
        else:
            self.stages.append(rec)

        self._stack.append(rec)
        t0 = time.perf_counter()
        c0 = time.process_time()
        try:
            yield rec
        except Exception as exc:  # noqa: BLE001
            rec.ok, rec.error = False, str(exc)
            if critical:
                self.log(f"stage {stage_id} FAILED: {exc}", level="ERROR")
                raise
            self.log(f"stage {stage_id} degraded (non-critical): {exc}", level="WARN")
        finally:
            rec.duration_ms = (time.perf_counter() - t0) * 1000
            rec.cpu_ms = (time.process_time() - c0) * 1000
            rec.ended_at = _utc_now()
            self._stack.pop()

    def record_crawl(
        self,
        url: str,
        duration_ms: float,
        *,
        ok: bool = True,
        output_file: str | None = None,
        error: str | None = None,
        bytes_downloaded: int = 0,
    ) -> None:
        if not self.enabled:
            return
        self.crawls.append(
            CrawlRecord(
                url=url,
                duration_ms=duration_ms,
                ok=ok,
                output_file=output_file,
                error=error,
                bytes_downloaded=bytes_downloaded,
            )
        )

    def record_llm_call(self, record: LlmCallRecord) -> None:
        if not self.enabled:
            return
        self.llm_calls.append(record)

    def record_tool_call(
        self,
        tool: str,
        args: dict[str, Any],
        *,
        ok: bool,
        duration_ms: float,
        detail: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        self.tool_calls.append(
            ToolCallRecord(tool=tool, args=args, ok=ok, duration_ms=duration_ms, detail=detail)
        )

    def build_report(self) -> dict[str, Any]:
        total_ms = (time.perf_counter() - self._run_t0) * 1000
        total_cpu_ms = (time.process_time() - self._run_cpu0) * 1000
        llm_ms = sum(c.duration_ms for c in self.llm_calls)
        pt = sum(c.prompt_tokens or 0 for c in self.llm_calls)
        ct = sum(c.completion_tokens or 0 for c in self.llm_calls)
        tt = sum(c.total_tokens or 0 for c in self.llm_calls)
        estimated = any(c.tokens_estimated for c in self.llm_calls)

        failures = _failed_stages(self.stages)
        llm_cfg = self.cfg.get("llm") or {}
        ingest_ms = sum(
            float(st.duration_ms)
            for st in self.stages
            if st.id in ("ingestion.preflight", "ingestion.crawl4ai", "ingestion.structured")
        )
        cache_root = cache_dir(self.cfg) / self.prefix if self.prefix else None
        preflight = preflight_dir(self.cfg) / f"preflight_{self.prefix}.json"
        network = summarize_network(
            [c.to_dict() for c in self.crawls],
            cache_root=cache_root,
            preflight_path=preflight if preflight.exists() else None,
            ingest_duration_ms=ingest_ms or None,
        )
        return {
            "schema": "direct_pipeline_py.diagnostics/v1",
            "prefix": self.prefix,
            "poc_id": "ai_digest",
            "status": "degraded" if failures else "ok",
            "started_at": self.run_started_at,
            "finished_at": _utc_now(),
            "total_duration_ms": round(total_ms, 1),
            "total_cpu_ms": round(total_cpu_ms, 1),
            "environment": self.environment,
            "network": network,
            "llm": {
                "enabled": bool(llm_cfg.get("enabled")),
                "provider": llm_cfg.get("provider"),
                "model": llm_cfg.get("model"),
            },
            "stages": [s.to_dict() for s in self.stages],
            "llm_calls": [c.to_dict() for c in self.llm_calls],
            "crawls": [c.to_dict() for c in self.crawls],
            "tool_calls": [t.to_dict() for t in self.tool_calls],
            "log": [l.to_dict() for l in self.logs],
            "totals": {
                "stage_count": len(self.stages),
                "llm_call_count": len(self.llm_calls),
                "llm_duration_ms": round(llm_ms, 1),
                "llm_share_pct": round(100 * llm_ms / total_ms, 1) if total_ms else 0,
                "crawl_count": len(self.crawls),
                "crawl_duration_ms": round(sum(c.duration_ms for c in self.crawls), 1),
                "tool_call_count": len(self.tool_calls),
                "tool_calls_ok": sum(1 for t in self.tool_calls if t.ok),
                "stage_failures": len(failures),
                "failed_stages": [f.id for f in failures],
                "prompt_tokens": pt or None,
                "completion_tokens": ct or None,
                "total_tokens": tt or None,
                "tokens_estimated": estimated,
            },
        }

    def write(self, cfg: dict[str, Any]) -> Path:
        dcfg = cfg.get("diagnostics") or {}
        out_dir = diagnostics_dir(cfg)
        out_dir.mkdir(parents=True, exist_ok=True)

        report = self.build_report()
        from lib.report_source import enrich_diagnostics_with_source
        from llm_pipeline.paths import diagnostics_dir

        report = enrich_diagnostics_with_source(report, diagnostics_dir(self.cfg))
        json_path = out_dir / f"{self.prefix}.diagnostics.json"
        html_path = out_dir / f"{self.prefix}.diagnostics.html"
        log_path = out_dir / f"{self.prefix}.run.log"
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        html_path.write_text(_render_waterfall_html(report), encoding="utf-8")
        log_path.write_text(_render_run_log(report), encoding="utf-8")

        print(f"  OK diagnostics {json_path}")
        print(f"  OK diagnostics {html_path}")
        print(f"  OK run log     {log_path}")
        rebuild_diagnostics_archive(out_dir, self.cfg)
        return json_path


def rebuild_diagnostics_waterfall_pages(diag_dir: Path, cfg: dict[str, Any] | None = None) -> int:
    """Re-render per-run waterfall HTML from existing diagnostics JSON files."""
    from llm_pipeline.config import load_config

    if cfg is None:
        cfg = load_config()

    count = 0
    for path in sorted(diag_dir.glob("*.diagnostics.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        prefix = data.get("prefix") or path.stem.replace(".diagnostics", "")
        data = _enrich_report_paths(data, cfg, prefix)
        from lib.report_source import enrich_diagnostics_with_source

        data = enrich_diagnostics_with_source(data, diag_dir)
        html_path = diag_dir / f"{prefix}.diagnostics.html"
        html_path.write_text(_render_waterfall_html(data), encoding="utf-8")
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        count += 1
    if count:
        print(f"  OK rebuilt {count} diagnostics waterfall page(s)")
    return count


def backfill_diagnostics_json_files(diag_dir: Path, cfg: dict[str, Any] | None = None) -> int:
    """Add environment/network to legacy diagnostics JSON (in place)."""
    from llm_pipeline.config import load_config

    if cfg is None:
        cfg = load_config()

    count = 0
    for path in sorted(diag_dir.glob("*.diagnostics.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        prefix = data.get("prefix") or path.stem.replace(".diagnostics", "")
        enriched = _enrich_report_paths(data, cfg, prefix)
        from lib.report_source import enrich_diagnostics_with_source

        enriched = enrich_diagnostics_with_source(enriched, diag_dir)
        had_env = bool((data.get("environment") or {}).get("platform_kind"))
        had_net = bool(
            (data.get("network") or {}).get("bytes_downloaded")
            or (data.get("network") or {}).get("throughput_mbps") is not None
        )
        had_source = bool(data.get("report_source_badge"))
        if not had_env or not had_net or not had_source:
            path.write_text(json.dumps(enriched, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            count += 1
    if count:
        print(f"  OK backfilled environment/network on {count} diagnostics JSON file(s)")
    return count


def _enrich_report_paths(data: dict[str, Any], cfg: dict[str, Any], prefix: str) -> dict[str, Any]:
    cache_root = cache_dir(cfg) / prefix
    preflight = preflight_dir(cfg) / f"preflight_{prefix}.json"
    return enrich_diagnostics_report(
        data,
        cache_root=cache_root if cache_root.is_dir() else None,
        preflight_path=preflight if preflight.exists() else None,
    )


class _NullCollector(DiagnosticCollector):
    def __init__(self) -> None:
        super().__init__(prefix="", cfg={}, enabled=False)


_NULL = _NullCollector()


# ── LLM instrumentation ──────────────────────────────────────────────────────────


def instrumented_llm_call(
    client: Any,
    model: str,
    max_retries: int,
    prompt: str,
    response_model: type,
    *,
    call_name: str,
) -> Any:
    """Wrap Instructor LLM call with timing + token usage capture."""
    col = get_collector()
    if not col.enabled:
        return _raw_llm_call(client, model, max_retries, prompt, response_model)

    started = _utc_now()
    t0 = time.perf_counter()
    prompt_chars = len(prompt)
    usage: dict[str, Any] = {}
    ollama: dict[str, Any] = {}
    ok = True
    err: str | None = None
    result: Any = None

    try:
        result, usage, ollama = _raw_llm_call_with_usage(
            client, model, max_retries, prompt, response_model
        )
    except Exception as exc:
        ok = False
        err = str(exc)
        raise
    finally:
        duration_ms = (time.perf_counter() - t0) * 1000
        pt, ct, tt, estimated = _normalize_tokens(usage, prompt_chars, ollama)
        col.record_llm_call(
            LlmCallRecord(
                name=call_name,
                model=model,
                started_at=started,
                ended_at=_utc_now(),
                duration_ms=duration_ms,
                prompt_chars=prompt_chars,
                prompt_tokens=pt,
                completion_tokens=ct,
                total_tokens=tt,
                tokens_estimated=estimated,
                max_retries=max_retries,
                ok=ok,
                error=err,
                ollama=ollama,
            )
        )

    return result


def _raw_llm_call(
    client: Any,
    model: str,
    max_retries: int,
    prompt: str,
    response_model: type,
) -> Any:
    result, _, _ = _raw_llm_call_with_usage(client, model, max_retries, prompt, response_model)
    return result


def _raw_llm_call_with_usage(
    client: Any,
    model: str,
    max_retries: int,
    prompt: str,
    response_model: type,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_model": response_model,
        "max_retries": max_retries,
    }
    create_wc = getattr(client.chat.completions, "create_with_completion", None)
    if callable(create_wc):
        result, completion = create_wc(**kwargs)
        return result, _extract_openai_usage(completion), _extract_ollama_fields(completion)

    result = client.chat.completions.create(**kwargs)
    return result, {}, {}


def _extract_openai_usage(completion: Any) -> dict[str, int]:
    usage = getattr(completion, "usage", None)
    if usage is None:
        return {}
    if isinstance(usage, dict):
        raw = usage
    elif hasattr(usage, "model_dump"):
        raw = usage.model_dump()
    else:
        raw = {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
    out: dict[str, int] = {}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
        val = raw.get(key)
        if val is not None:
            out[key] = int(val)
    return out


def _extract_ollama_fields(completion: Any) -> dict[str, Any]:
    """Ollama-native timing/token fields when exposed on the raw completion."""
    raw: dict[str, Any] = {}
    if hasattr(completion, "model_dump"):
        try:
            raw = completion.model_dump()
        except Exception:
            raw = {}
    for key in (
        "prompt_eval_count",
        "eval_count",
        "prompt_eval_duration",
        "eval_duration",
        "load_duration",
        "total_duration",
    ):
        val = raw.get(key)
        if val is not None:
            raw[key] = val
    return {k: raw[k] for k in raw if k in (
        "prompt_eval_count", "eval_count", "prompt_eval_duration",
        "eval_duration", "load_duration", "total_duration",
    )}


def _normalize_tokens(
    usage: dict[str, int],
    prompt_chars: int,
    ollama: dict[str, Any],
) -> tuple[int | None, int | None, int | None, bool]:
    pt = usage.get("prompt_tokens")
    ct = usage.get("completion_tokens")
    tt = usage.get("total_tokens")

    if pt is None and ollama.get("prompt_eval_count") is not None:
        pt = int(ollama["prompt_eval_count"])
    if ct is None and ollama.get("eval_count") is not None:
        ct = int(ollama["eval_count"])
    if tt is None and pt is not None and ct is not None:
        tt = pt + ct

    estimated = False
    if pt is None and ct is None:
        pt = max(1, prompt_chars // 4)
        estimated = True
    return pt, ct, tt, estimated


def _ms_to_label(ms: float) -> str:
    if ms >= 60_000:
        return f"{ms / 60_000:.1f}m"
    if ms >= 1000:
        return f"{ms / 1000:.1f}s"
    return f"{ms:.0f}ms"


def _render_waterfall_html(report: dict[str, Any]) -> str:
    total = float(report.get("total_duration_ms") or 1)
    totals = report.get("totals") or {}
    llm = report.get("llm") or {}
    stages = report.get("stages") or []
    calls = report.get("llm_calls") or []
    crawls = report.get("crawls") or []
    prefix = report.get("prefix", "")

    crawl_rows: list[str] = []
    crawl_t0 = float(stages[0].get("duration_ms") or 0) if stages else 0.0
    for cr in crawls:
        dur = float(cr.get("duration_ms") or 0)
        left = 100 * crawl_t0 / total
        width = max(0.3, 100 * dur / total)
        crawl_t0 += dur
        host = cr.get("url", "").split("//")[-1][:40]
        status = "" if cr.get("ok", True) else " FAIL"
        crawl_rows.append(
            f"""<div class="row sub">
  <span class="label" title="{cr.get('url', '')}">{host}</span>
  <div class="track"><div class="bar crawl" style="left:{left:.2f}%;width:{width:.2f}%"></div></div>
  <span class="time">{_ms_to_label(dur)}{status}</span>
</div>"""
        )

    # Flat timeline: top-level stages + LLM calls as sub-rows
    timeline: list[tuple[str, str, float, float, str]] = []
    offset = 0.0
    for st in stages:
        dur = float(st.get("duration_ms") or 0)
        timeline.append((st.get("id", ""), st.get("label", ""), offset, dur, "stage"))
        offset += dur

    llm_offset = 0.0
    for st in stages:
        if st.get("id") == "enrich":
            llm_offset = sum(float(s.get("duration_ms") or 0) for s in stages if s.get("id") != "enrich")
            break

    call_rows: list[str] = []
    call_t0 = llm_offset
    for c in calls:
        dur = float(c.get("duration_ms") or 0)
        left = 100 * call_t0 / total
        width = max(0.4, 100 * dur / total)
        tok = c.get("total_tokens")
        tok_lbl = f"{tok:,} tok" if tok else f"~{c.get('prompt_chars', 0) // 4:,} tok?"
        status = "" if c.get("ok", True) else " failed"
        call_rows.append(
            f"""<div class="row sub">
  <span class="label" title="{c.get('name', '')}">{c.get('name', '')}</span>
  <div class="track"><div class="bar llm" style="left:{left:.2f}%;width:{width:.2f}%"></div></div>
  <span class="time">{_ms_to_label(dur)} · {tok_lbl}{status}</span>
</div>"""
        )
        call_t0 += dur

    stage_rows: list[str] = []
    offset = 0.0
    colors = ["#3b82f6", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b"]
    for i, st in enumerate(stages):
        dur = float(st.get("duration_ms") or 0)
        left = 100 * offset / total
        width = max(0.8, 100 * dur / total)
        failed = not st.get("ok", True)
        color = "#ef4444" if failed else colors[i % len(colors)]
        if failed:
            kind = "degraded" if not st.get("critical", True) else "FAILED"
            status = f" · {kind}"
            title = st.get("error") or kind
        else:
            status, title = "", st.get("label", st.get("id", ""))
        stage_rows.append(
            f"""<div class="row">
  <span class="label" title="{title}">{st.get('label', st.get('id', ''))}</span>
  <div class="track"><div class="bar" style="left:{left:.2f}%;width:{width:.2f}%;background:{color}"></div></div>
  <span class="time">{_ms_to_label(dur)}{status}</span>
</div>"""
        )
        offset += dur

    tok_est = " (estimated)" if totals.get("tokens_estimated") else ""
    pt = totals.get("prompt_tokens")
    ct = totals.get("completion_tokens")
    tt = totals.get("total_tokens")

    status = report.get("status", "ok")
    failed = int(totals.get("stage_failures") or 0)
    badge = (
        f'<span class="badge ok">OK</span>' if status == "ok"
        else f'<span class="badge bad">DEGRADED · {failed} stage(s)</span>'
    )
    page_title = report.get("title") or "Pipeline diagnostics"
    agents = report.get("agents") or {}
    graph_line = (
        f'<p class="sub">{html.escape(agents.get("graph", ""))}</p>'
        if agents.get("graph")
        else ""
    )
    log_rows = "".join(
        f'<div class="logline {ln.get("level", "INFO").lower()}">'
        f'<span class="lt">{ln.get("ts", "")[11:19]}</span>'
        f'<span class="ll">{html.escape(ln.get("level", ""))}</span>'
        f'<span class="ls">{html.escape(ln.get("stage") or "")}</span>'
        f'<span class="lm">{html.escape(ln.get("message", ""))}</span></div>'
        for ln in (report.get("log") or [])
    )

    env = report.get("environment") or {}
    net = report.get("network") or {}
    env_line = format_env_line(env)
    net_line = format_net_line(net)
    hw_cards = "".join(
        f'<div class="card hw-card"><div class="v">{html.escape(val)}</div>'
        f'<div class="k">{html.escape(label)}</div></div>'
        for label, val in hw_metric_cards(env, net)
    )

    from llm_pipeline.styles import diagnostics_waterfall_styles, theme_apply_script
    from lib.report_source import report_source_badge_html

    css = diagnostics_waterfall_styles()
    theme_js = theme_apply_script()
    source_seal = report_source_badge_html(report)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Diagnostics | {prefix}</title>
  <style>
{css}
  </style>
  <script>{theme_js}</script>
</head>
<body class="diag-page">
  <h1 class="diag-head">{source_seal}<span>{page_title} {badge}</span></h1>
  {graph_line}
  <p class="meta">{prefix} · {report.get('started_at', '')} → {report.get('finished_at', '')}<br>
  Model: {llm.get('model', '—')} ({llm.get('provider', '')})</p>
  {f'<p class="env-block"><strong>Hardware</strong> {html.escape(env_line)}</p>' if env_line else ''}
  {f'<p class="env-block"><strong>Network</strong> {html.escape(net_line)}</p>' if net_line else ''}

  <h2>Hardware profile</h2>
  <div class="cards hw-cards">{hw_cards}</div>

  <h2>Run totals</h2>
  <div class="cards">
    <div class="card"><div class="v">{_ms_to_label(float(report.get('total_duration_ms') or 0))}</div><div class="k">Wall time</div></div>
    <div class="card"><div class="v">{_ms_to_label(float(report.get('total_cpu_ms') or 0))}</div><div class="k">CPU time</div></div>
    <div class="card"><div class="v">{totals.get('llm_call_count', 0)}</div><div class="k">LLM calls</div></div>
    <div class="card"><div class="v">{_ms_to_label(float(totals.get('llm_duration_ms') or 0))}</div><div class="k">LLM time ({totals.get('llm_share_pct', 0)}%)</div></div>
    <div class="card"><div class="v">{f"{tt:,}" if tt else "—"}{tok_est}</div><div class="k">Total tokens</div></div>
    <div class="card"><div class="v">{f"{pt:,}" if pt else "—"} / {f"{ct:,}" if ct else "—"}</div><div class="k">Prompt / completion</div></div>
  </div>

  <h2>Stage waterfall</h2>
  <div class="waterfall">
    {''.join(stage_rows)}
    <div class="axis"><span>0</span><span>{_ms_to_label(total / 2)}</span><span>{_ms_to_label(total)}</span></div>
  </div>

  <h2>Crawl4AI fetches</h2>
  <div class="waterfall">
    {''.join(crawl_rows) if crawl_rows else '<p class="meta">No crawls recorded.</p>'}
  </div>

  <h2>LLM calls</h2>
  <div class="waterfall">
    {''.join(call_rows) if call_rows else '<p class="meta">No LLM calls recorded.</p>'}
  </div>

  <h2>LLM call table</h2>
  <table>
    <thead><tr><th>Call</th><th>Duration</th><th class="num">Prompt tok</th><th class="num">Completion tok</th><th class="num">Total</th></tr></thead>
    <tbody>
      {''.join(_call_table_row(c) for c in calls)}
    </tbody>
  </table>

  <h2>Run log</h2>
  <div class="runlog">
    {log_rows if log_rows else '<p class="meta">No log lines recorded.</p>'}
  </div>

  <p class="meta" style="margin-top:2rem">JSON: <a href="{prefix}.diagnostics.json">{prefix}.diagnostics.json</a> · Log: <a href="{prefix}.run.log">{prefix}.run.log</a></p>
</body>
</html>"""


def _render_run_log(report: dict[str, Any]) -> str:
    """Plain-text, greppable run log: a header line plus one line per event."""
    head = (
        f"# AI Digest run log  prefix={report.get('prefix', '')}  "
        f"status={report.get('status', 'ok')}  "
        f"started={report.get('started_at', '')}  finished={report.get('finished_at', '')}"
    )
    lines = [head]
    for ln in report.get("log") or []:
        stage = ln.get("stage") or "-"
        lines.append(
            f"{ln.get('ts', '')}  {ln.get('level', 'INFO'):<5}  [{stage}]  {ln.get('message', '')}"
        )
    return "\n".join(lines) + "\n"


def _call_table_row(c: dict[str, Any]) -> str:
    est = " ~" if c.get("tokens_estimated") else ""
    pt = c.get("prompt_tokens")
    ct = c.get("completion_tokens")
    tt = c.get("total_tokens")
    return (
        f"<tr><td>{c.get('name', '')}</td>"
        f"<td>{_ms_to_label(float(c.get('duration_ms') or 0))}</td>"
        f"<td class='num'>{f'{pt:,}{est}' if pt else '—'}</td>"
        f"<td class='num'>{f'{ct:,}' if ct else '—'}</td>"
        f"<td class='num'>{f'{tt:,}' if tt else '—'}</td></tr>"
    )
