"""Agentic Hermes run diagnostics — kanban task waterfall + LLM/tool telemetry."""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from lib.paths import REPO_ROOT

HERMES_ROOT = REPO_ROOT / "agentic" / "hermes"
RUNTIME = HERMES_ROOT / ".runtime"

from tools.profiles import (
    DISPLAY,
    LEGACY,
    LIBRARIAN,
    PIPELINE_GRAPH,
    RESEARCHER,
    SYNTHESIZER,
    normalize,
)

PROFILE_LABELS = {**DISPLAY, **{k: v.title() for k, v in LEGACY.items()}}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _ms_between(start: str, end: str) -> float:
    return max(0.0, (_parse_utc(end) - _parse_utc(start)).total_seconds() * 1000)


@dataclass
class TaskRecord:
    task_id: str
    title: str
    profile: str
    started_at: str
    ended_at: str
    duration_ms: float
    ok: bool = True
    status: str = "done"
    meta: dict[str, Any] = field(default_factory=dict)

    def to_stage(self) -> dict[str, Any]:
        label = PROFILE_LABELS.get(self.profile, self.profile.title())
        return {
            "id": f"task.{self.task_id}",
            "label": f"{self.title} · {label}",
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_ms": round(self.duration_ms, 1),
            "cpu_ms": 0.0,
            "ok": self.ok,
            "critical": True,
            "error": None if self.ok else self.status,
            "meta": {"profile": self.profile, "task_id": self.task_id, **self.meta},
            "children": [],
        }


@dataclass
class PhaseRecord:
    phase_id: str
    label: str
    started_at: str
    ended_at: str | None = None
    duration_ms: float = 0.0
    ok: bool = True
    children: list[TaskRecord] = field(default_factory=list)

    def to_stage(self) -> dict[str, Any]:
        return {
            "id": self.phase_id,
            "label": self.label,
            "started_at": self.started_at,
            "ended_at": self.ended_at or self.started_at,
            "duration_ms": round(self.duration_ms, 1),
            "cpu_ms": 0.0,
            "ok": self.ok,
            "critical": True,
            "error": None,
            "meta": {},
            "children": [c.to_stage() for c in self.children],
        }


_active: AgentDiagnosticsCollector | None = None


class AgentDiagnosticsCollector:
    def __init__(self, prefix: str, cfg: dict[str, Any]) -> None:
        self.prefix = prefix
        self.cfg = cfg
        self.started_at = _utc_now()
        self.phases: list[PhaseRecord] = []
        self.tasks: list[TaskRecord] = []
        self.logs: list[dict[str, Any]] = []
        self._open_phase: PhaseRecord | None = None

    def log(self, message: str, *, level: str = "INFO", stage: str | None = None) -> None:
        entry = {"ts": _utc_now(), "level": level, "stage": stage, "message": message}
        self.logs.append(entry)
        print(f"  [{level}] {message}")

    @contextmanager
    def phase(self, phase_id: str, label: str) -> Iterator[PhaseRecord]:
        rec = PhaseRecord(phase_id=phase_id, label=label, started_at=_utc_now())
        self._open_phase = rec
        t0 = time.perf_counter()
        try:
            yield rec
            rec.ok = True
        except Exception as exc:
            rec.ok = False
            self.log(str(exc), level="ERROR", stage=phase_id)
            raise
        finally:
            rec.duration_ms = (time.perf_counter() - t0) * 1000
            rec.ended_at = _utc_now()
            self.phases.append(rec)
            self._open_phase = None

    def record_task(
        self,
        *,
        task_id: str,
        title: str,
        profile: str,
        duration_ms: float,
        started_at: str | None = None,
        ended_at: str | None = None,
        ok: bool = True,
        status: str = "done",
        meta: dict[str, Any] | None = None,
    ) -> None:
        end = ended_at or _utc_now()
        start = started_at or end
        if duration_ms <= 0 and started_at and ended_at:
            duration_ms = _ms_between(started_at, ended_at)
        task = TaskRecord(
            task_id=task_id,
            title=title,
            profile=profile,
            started_at=start,
            ended_at=end,
            duration_ms=duration_ms,
            ok=ok,
            status=status,
            meta=meta or {},
        )
        self.tasks.append(task)
        if self._open_phase is not None:
            self._open_phase.children.append(task)

    def build_report(self) -> dict[str, Any]:
        from llm_pipeline.diagnostics import get_collector
        from llm_pipeline.environment import capture_environment, enrich_diagnostics_report

        finished_at = _utc_now()
        total_ms = _ms_between(self.started_at, finished_at)
        if self.phases:
            total_ms = sum(p.duration_ms for p in self.phases)

        pipeline = get_collector()
        llm_calls = [c.to_dict() for c in pipeline.llm_calls] if pipeline and pipeline.enabled else []
        tool_calls = [t.to_dict() for t in pipeline.tool_calls] if pipeline and pipeline.enabled else []

        llm_ms = sum(float(c.get("duration_ms") or 0) for c in llm_calls)
        pt = sum(int(c.get("prompt_tokens") or 0) for c in llm_calls if c.get("prompt_tokens"))
        ct = sum(int(c.get("completion_tokens") or 0) for c in llm_calls if c.get("completion_tokens"))
        tt = pt + ct if pt or ct else None

        llm_cfg = self.cfg.get("llm") or {}
        env = capture_environment()
        nested_tasks = sum(len(p.children) for p in self.phases)
        task_count = nested_tasks + len(self.tasks)
        report: dict[str, Any] = {
            "schema": "agentic_hermes.diagnostics/v1",
            "title": "Hermes agent diagnostics",
            "prefix": self.prefix,
            "poc_id": "agentic_hermes",
            "status": "ok",
            "started_at": self.started_at,
            "finished_at": finished_at,
            "total_duration_ms": round(total_ms, 1),
            "total_cpu_ms": 0.0,
            "environment": env,
            "network": {},
            "llm": {
                "enabled": bool(llm_cfg.get("enabled", True)),
                "provider": llm_cfg.get("provider"),
                "model": llm_cfg.get("model"),
            },
            "agents": {
                "graph": PIPELINE_GRAPH,
                "profiles": list(PROFILE_LABELS.keys()),
                "task_count": task_count,
            },
            "stages": [p.to_stage() for p in self.phases],
            "llm_calls": llm_calls,
            "crawls": [],
            "tool_calls": tool_calls,
            "log": self.logs,
            "totals": {
                "stage_count": len(self.phases),
                "task_count": task_count,
                "llm_call_count": len(llm_calls),
                "llm_duration_ms": round(llm_ms, 1),
                "llm_share_pct": round(100 * llm_ms / total_ms, 1) if total_ms else 0,
                "tool_call_count": len(tool_calls),
                "tool_calls_ok": sum(1 for t in tool_calls if t.get("ok")),
                "stage_failures": 0,
                "failed_stages": [],
                "prompt_tokens": pt or None,
                "completion_tokens": ct or None,
                "total_tokens": tt,
                "tokens_estimated": not bool(tt),
            },
        }
        enrich_diagnostics_report(report)
        return report

    def write(self) -> Path:
        from llm_pipeline.diagnostics import _render_run_log, _render_waterfall_html
        from llm_pipeline.diagnostics_frame import rebuild_diagnostics_archive
        from llm_pipeline.paths import diagnostics_dir

        out_dir = diagnostics_dir(self.cfg)
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
        print(f"  OK agent diagnostics {json_path.relative_to(REPO_ROOT)}")
        print(f"  OK agent diagnostics {html_path.relative_to(REPO_ROOT)}")
        rebuild_diagnostics_archive(out_dir, self.cfg)
        return json_path


def init_agent_diagnostics(prefix: str, cfg: dict[str, Any]) -> AgentDiagnosticsCollector:
    global _active
    _active = AgentDiagnosticsCollector(prefix=prefix, cfg=cfg)
    return _active


def get_agent_diagnostics() -> AgentDiagnosticsCollector | None:
    return _active


def finish_agent_diagnostics(cfg: dict[str, Any] | None = None) -> Path | None:
    global _active
    col = _active
    _active = None
    if col is None:
        return None
    return col.write()


def _artifact_times(prefix: str) -> dict[str, float]:
    base = RUNTIME / "artifacts" / prefix
    out: dict[str, float] = {}
    for rel in (
        "research/evaluation_test_topic.md",
        "librarian.md",
        "digest.json",
        "handover.json",
    ):
        path = base / rel
        if path.is_file():
            out[rel] = path.stat().st_mtime
    report = HERMES_ROOT / "reports" / f"{prefix}.json"
    if report.is_file():
        out["report.json"] = report.stat().st_mtime
    return out


def rebuild_from_artifacts(prefix: str, cfg: dict[str, Any] | None = None) -> Path:
    """Reconstruct diagnostics from handover receipt + artifact mtimes (retroactive runs)."""
    if cfg is None:
        from tools.baseline import agentic_config

        cfg = agentic_config()

    handover_path = RUNTIME / "artifacts" / prefix / "handover.json"
    if not handover_path.is_file():
        raise FileNotFoundError(f"missing handover receipt: {handover_path}")

    handover = json.loads(handover_path.read_text(encoding="utf-8"))
    digest_path = RUNTIME / "artifacts" / prefix / "digest.json"
    digest_generated = None
    if digest_path.is_file():
        digest_generated = json.loads(digest_path.read_text(encoding="utf-8")).get("generated_at")

    mtimes = _artifact_times(prefix)
    completed_at = handover.get("completed_at") or _utc_now()

    def _ts(key: str, fallback: str) -> str:
        if key in mtimes:
            return datetime.fromtimestamp(mtimes[key], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return fallback

    research_end = _ts("research/evaluation_test_topic.md", completed_at)
    librarian_end = _ts("librarian.md", research_end)
    synth_end = digest_generated or _ts("digest.json", librarian_end)
    render_end = completed_at

    research_start = datetime.fromtimestamp(
        mtimes.get("research/evaluation_test_topic.md", 0) - 90, tz=timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ") if "research/evaluation_test_topic.md" in mtimes else research_end

    col = AgentDiagnosticsCollector(prefix=prefix, cfg=cfg)
    col.started_at = research_start

    setup = PhaseRecord(
        phase_id="go.setup",
        label="Concierge · board setup",
        started_at=research_start,
        ended_at=research_start,
        duration_ms=min(30_000.0, _ms_between(research_start, research_end) * 0.05),
    )
    col.phases.append(setup)

    research_phase = PhaseRecord(
        phase_id="go.research",
        label="Research workers",
        started_at=research_start,
        ended_at=research_end,
        duration_ms=_ms_between(research_start, research_end),
    )
    for task in handover.get("tasks") or []:
        if normalize(str(task.get("assignee") or "")) != RESEARCHER:
            continue
        research_phase.children.append(
            TaskRecord(
                task_id=str(task.get("id") or "research"),
                title=str(task.get("title") or "Research"),
                profile=normalize(str(task.get("assignee") or RESEARCHER)),
                started_at=research_start,
                ended_at=research_end,
                duration_ms=_ms_between(research_start, research_end),
                ok=task.get("status") == "done",
                status=str(task.get("status") or "done"),
            )
        )
    col.phases.append(research_phase)

    lib_start = research_end
    lib_phase = PhaseRecord(
        phase_id="go.librarian",
        label="Librarian · merge & classify",
        started_at=lib_start,
        ended_at=librarian_end,
        duration_ms=_ms_between(lib_start, librarian_end),
    )
    for task in handover.get("tasks") or []:
        if normalize(str(task.get("assignee") or "")) == LIBRARIAN:
            lib_phase.children.append(
                TaskRecord(
                    task_id=str(task.get("id") or "librarian"),
                    title=str(task.get("title") or "Librarian"),
                    profile=LIBRARIAN,
                    started_at=lib_start,
                    ended_at=librarian_end,
                    duration_ms=_ms_between(lib_start, librarian_end),
                    ok=task.get("status") == "done",
                    status=str(task.get("status") or "done"),
                )
            )
    col.phases.append(lib_phase)

    syn_start = librarian_end
    syn_phase = PhaseRecord(
        phase_id="go.synthesizer",
        label="Synthesizer · digest JSON",
        started_at=syn_start,
        ended_at=synth_end,
        duration_ms=_ms_between(syn_start, synth_end),
    )
    for task in handover.get("tasks") or []:
        if normalize(str(task.get("assignee") or "")) == SYNTHESIZER:
            syn_phase.children.append(
                TaskRecord(
                    task_id=str(task.get("id") or "synthesizer"),
                    title=str(task.get("title") or "Synthesize digest"),
                    profile=SYNTHESIZER,
                    started_at=syn_start,
                    ended_at=synth_end,
                    duration_ms=_ms_between(syn_start, synth_end),
                    ok=task.get("status") == "done",
                    status=str(task.get("status") or "done"),
                )
            )
    col.phases.append(syn_phase)

    render_phase = PhaseRecord(
        phase_id="go.render",
        label="Render · validate & HTML",
        started_at=synth_end,
        ended_at=render_end,
        duration_ms=_ms_between(synth_end, render_end),
    )
    col.phases.append(render_phase)
    col.log("Rebuilt from handover.json + artifact mtimes", stage="rebuild")

    global _active
    _active = col
    try:
        return col.write()
    finally:
        _active = None
