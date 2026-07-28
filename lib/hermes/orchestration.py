"""AI Digest kanban orchestration — board status and artifact gates for Concierge."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

HERMES_HOME = Path.home() / ".hermes"

LIBRARIAN_TITLE = "Librarian: merge & classify"
SYNTHESIZER_TITLE = "Synthesize digest"

_RUN_PREFIX_RE = re.compile(r"run prefix [`'\"]?(\d{14})[`'\"]?", re.I)
_ACTIVE_STATUSES = frozenset({"running", "ready", "in_progress"})


def _hermes_bin() -> str | None:
    return shutil.which("hermes")


def kanban_list(*, raise_on_error: bool = False) -> list[dict[str, Any]]:
    hermes = _hermes_bin()
    if not hermes:
        if raise_on_error:
            raise RuntimeError("hermes not on PATH")
        return []
    proc = subprocess.run(
        [hermes, "kanban", "list", "--json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        if raise_on_error:
            raise RuntimeError(proc.stderr or proc.stdout or "kanban list failed")
        return []
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"kanban list: JSON decode error — gateway may be down: {exc}")
        if raise_on_error:
            raise
        return []


def kanban_show(task_id: str) -> dict[str, Any]:
    hermes = _hermes_bin()
    if not hermes:
        raise RuntimeError("hermes not on PATH")
    proc = subprocess.run(
        [hermes, "kanban", "show", task_id, "--json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "kanban show failed")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(f"kanban show {task_id}: JSON decode error — gateway may be down: {exc}")
        if raise_on_error:
            raise
        return {}


def extract_run_prefix(text: str) -> str | None:
    """Parse ``run prefix `YYYYMMDDHHmmss``` from a kanban task body or comment."""
    match = _RUN_PREFIX_RE.search(text or "")
    return match.group(1) if match else None


def detect_run_prefix(rows: list[dict[str, Any]]) -> str | None:
    """Best-effort run prefix from digest board task bodies."""
    for row in rows:
        prefix = extract_run_prefix(str(row.get("body") or ""))
        if prefix:
            return prefix
        for comment in row.get("comments") or []:
            if isinstance(comment, dict):
                prefix = extract_run_prefix(str(comment.get("text") or comment.get("body") or ""))
            else:
                prefix = extract_run_prefix(str(comment))
            if prefix:
                return prefix
    return None


def _task_workspace(task: dict[str, Any]) -> Path:
    path = task.get("workspace_path")
    if path:
        return Path(path)
    return HERMES_HOME / "kanban" / "workspaces" / str(task["id"])


def _artifact_gate(assignee: str, workspace: Path) -> dict[str, Any]:
    from lib.hermes.artifacts import (
        validate_librarian_artifact,
        validate_researcher_artifact,
        validate_synthesizer_artifact,
    )

    role = normalize(assignee)
    if role == RESEARCHER:
        errors = validate_researcher_artifact(workspace)
        artifact = "output.md"
    elif role == LIBRARIAN:
        errors = validate_librarian_artifact(workspace)
        artifact = "librarian.md"
    elif role == SYNTHESIZER:
        errors = validate_synthesizer_artifact(workspace)
        artifact = "digest.json"
    else:
        return {"artifact": None, "gate_ok": None, "errors": []}

    return {
        "artifact": artifact,
        "gate_ok": not errors,
        "errors": errors,
        "artifact_exists": (workspace / artifact).is_file() if artifact else False,
    }


def _artifact_gate_with_runtime(
    role: str,
    workspace: Path,
    prefix: str,
    workspace_gate: dict[str, Any],
) -> dict[str, Any]:
    """If Hermes wiped scratch workspace, fall back to .runtime/artifacts cache."""
    if workspace_gate.get("gate_ok"):
        return workspace_gate
    from lib.hermes.runtime_store import run_dir

    run_path = run_dir(prefix)
    if role == LIBRARIAN:
        cached = run_path / "librarian.md"
        if cached.is_file():
            return _artifact_gate(role, run_path)
    elif role == SYNTHESIZER:
        cached = run_path / "digest.json"
        if cached.is_file():
            return _artifact_gate(role, run_path)
    return workspace_gate


def digest_board_rows(rows: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = rows if rows is not None else kanban_list()
    titles = {LIBRARIAN_TITLE, SYNTHESIZER_TITLE}
    return [
        r
        for r in rows
        if str(r.get("title", "")).startswith("Research:")
        or str(r.get("title", "")) in titles
    ]


def _role_summary(role_tasks: list[dict[str, Any]]) -> dict[str, Any]:
    if not role_tasks:
        return {"count": 0, "done": 0, "artifact_pass": 0, "all_pass": True}
    done = sum(1 for t in role_tasks if t.get("kanban_done"))
    passed = sum(1 for t in role_tasks if t.get("gate_ok") is True)
    gates = [t.get("gate_ok") for t in role_tasks if t.get("gate_ok") is not None]
    return {
        "count": len(role_tasks),
        "done": done,
        "artifact_pass": passed,
        "all_pass": bool(gates) and all(gates),
    }


def _report_paths(prefix: str) -> tuple[Path, Path]:
    from lib.paths import AGENTIC_ROOT

    reports = AGENTIC_ROOT / "reports"
    return reports / f"{prefix}.html", reports / f"{prefix}.json"


def infer_pipeline_phase(
    *,
    board_empty: bool,
    research: dict[str, Any],
    librarian: dict[str, Any] | None,
    synthesizer: dict[str, Any] | None,
    report_ready: bool,
    pipeline_artifacts_ok: bool = False,
) -> str:
    """Coarse pipeline phase for Concierge STATUS (not LLM judgment).

    Kanban ``done`` is not success — artifact gates decide readiness for render.
    """
    if board_empty:
        return "idle"
    if report_ready:
        return "complete"
    r_count = int(research.get("count") or 0)
    r_done = int(research.get("done") or 0)
    if r_count and r_done < r_count:
        return "research"
    lib_done = bool((librarian or {}).get("kanban_done"))
    syn_done = bool((synthesizer or {}).get("kanban_done"))
    lib_gate = (librarian or {}).get("gate_ok")
    syn_gate = (synthesizer or {}).get("gate_ok")
    if lib_done and lib_gate is False:
        return "blocked"
    if syn_done and syn_gate is False:
        return "blocked"
    if not lib_done:
        return "librarian"
    if not syn_done:
        return "synthesizer"
    if not pipeline_artifacts_ok:
        return "blocked"
    return "render"


def _status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(r.get("status") or "unknown") for r in rows)
    return dict(sorted(counts.items()))


def _active_tasks(rows: list[dict[str, Any]], limit: int = 5) -> list[dict[str, str]]:
    """Tasks currently running or next up (todo/ready)."""
    active: list[dict[str, str]] = []
    for row in rows:
        status = str(row.get("status") or "")
        if status in _ACTIVE_STATUSES:
            active.append(
                {
                    "id": str(row.get("id") or ""),
                    "title": str(row.get("title") or ""),
                    "status": status,
                    "assignee": str(row.get("assignee") or ""),
                }
            )
    if len(active) < limit:
        for row in rows:
            if str(row.get("status") or "") != "todo":
                continue
            active.append(
                {
                    "id": str(row.get("id") or ""),
                    "title": str(row.get("title") or ""),
                    "status": "todo",
                    "assignee": str(row.get("assignee") or ""),
                }
            )
            if len(active) >= limit:
                break
    return active[:limit]


def _task_ref(row: dict[str, Any]) -> dict[str, str]:
    """Compact kanban task reference for Concierge to repost in chat."""
    tid = str(row.get("id") or "")
    return {
        "id": tid,
        "title": str(row.get("title") or ""),
        "status": str(row.get("status") or ""),
        "assignee": str(row.get("assignee") or ""),
        "kanban_show": f"hermes kanban show {tid}" if tid else "",
    }


def build_board_navigation(digest_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Kanban task ids for locating the digest graph (research roots + fan-in hub)."""
    research_rows = [
        r for r in digest_rows if str(r.get("title", "")).startswith("Research:")
    ]
    librarian_row = next(
        (r for r in digest_rows if r.get("title") == LIBRARIAN_TITLE),
        None,
    )
    synthesizer_row = next(
        (r for r in digest_rows if r.get("title") == SYNTHESIZER_TITLE),
        None,
    )

    root_tasks = [_task_ref(r) for r in research_rows]
    librarian = _task_ref(librarian_row) if librarian_row else None
    synthesizer = _task_ref(synthesizer_row) if synthesizer_row else None
    # Librarian is the fan-in hub — best single anchor to find the run in Kanban UI.
    primary_anchor = librarian or (root_tasks[0] if root_tasks else synthesizer)

    return {
        "root_tasks": root_tasks,
        "librarian": librarian,
        "synthesizer": synthesizer,
        "primary_anchor": primary_anchor,
        "list_cmd": "hermes kanban list --json",
    }


def format_status_summary(payload: dict[str, Any]) -> list[str]:
    """Human-readable lines for Concierge to quote in chat."""
    lines: list[str] = []
    phase = str(payload.get("phase") or "unknown")
    prefix = payload.get("run_prefix")
    if prefix:
        lines.append(f"Run prefix: {prefix}")
    if payload.get("board_empty"):
        lines.append("Board is empty — no digest GO in progress.")
        latest = payload.get("latest_report_prefix")
        if latest:
            lines.append(f"Latest published report prefix: {latest}")
        return lines

    counts = payload.get("status_counts") or {}
    if counts:
        parts = [f"{k}={v}" for k, v in counts.items()]
        lines.append(f"Kanban tasks: {', '.join(parts)}")

    research = payload.get("research") or {}
    librarian = payload.get("librarian") or {}
    synthesizer = payload.get("synthesizer") or {}
    lines.append(
        f"Research: {research.get('done', 0)}/{research.get('count', 0)} done "
        f"({research.get('artifact_pass', 0)} passed artifact gate)"
    )
    if librarian.get("count"):
        lines.append(
            f"Librarian: {librarian.get('done', 0)}/{librarian.get('count', 0)} done "
            f"(gate {'ok' if librarian.get('all_pass') else 'pending'})"
        )
    if synthesizer.get("count"):
        lines.append(
            f"Synthesizer: {synthesizer.get('done', 0)}/{synthesizer.get('count', 0)} done "
            f"(gate {'ok' if synthesizer.get('all_pass') else 'pending'})"
        )

    phase_labels = {
        "idle": "idle (no board)",
        "research": "research fan-out",
        "librarian": "librarian merge",
        "synthesizer": "synthesizer JSON",
        "blocked": "BLOCKED — artifact gate failed (not ready for render)",
        "render": "awaiting validate/render",
        "complete": "report ready",
    }
    lines.append(f"Pipeline phase: {phase_labels.get(phase, phase)}")

    if not payload.get("pipeline_artifacts_ok") and not payload.get("report_ready"):
        lines.append(
            "NOT ready for render — kanban done ≠ pipeline success; fix artifact gates first."
        )
        for role_key, label in (("librarian", "Librarian"), ("synthesizer", "Synthesizer")):
            role = payload.get(role_key) or {}

    return lines


def board_status(*, raise_on_error: bool = False) -> dict[str, Any]:
    """Current kanban board status for Concierge STATUS command."""
    rows = kanban_list() if not raise_on_error else kanban_list(raise_on_error=True)
    digest_rows = digest_board_rows(rows)

    research_rows = [r for r in digest_rows if str(r.get("title", "")).startswith("Research:")]
    librarian_row = next((r for r in digest_rows if r.get("title") == LIBRARIAN_TITLE), None)
    synthesizer_row = next((r for r in digest_rows if r.get("title") == SYNTHESIZER_TITLE), None)

    research_summary = _role_summary(research_rows)
    librarian_summary = _role_summary([librarian_row]) if librarian_row else {"count": 0, "done": 0, "artifact_pass": 0, "all_pass": True}
    synthesizer_summary = _role_summary([synthesizer_row]) if synthesizer_row else {"count": 0, "done": 0, "artifact_pass": 0, "all_pass": True}

    # Artifact gates for librarian/synthesizer
    lib_gate = None
    syn_gate = None
    if librarian_row:
        ws = _task_workspace(librarian_row)
        lib_gate = _artifact_gate(LIBRARIAN_TITLE.split(":")[0].strip(), ws).get("gate_ok")
    if synthesizer_row:
        ws = _task_workspace(synthesizer_row)
        syn_gate = _artifact_gate(SYNTHESIZER_TITLE.split(":")[0].strip(), ws).get("gate_ok")

    report_html, report_json = _report_paths(str(detect_run_prefix(rows) or ""))
    report_ready = report_html.is_file() if report_html else False
    pipeline_artifacts_ok = bool(lib_gate) and bool(syn_gate)

    phase = infer_pipeline_phase(
        board_empty=len(digest_rows) == 0,
        research=research_summary,
        librarian={"kanban_done": bool(librarian_row and librarian_row.get("kanban_done")), "gate_ok": lib_gate} if librarian_row else None,
        synthesizer={"kanban_done": bool(synthesizer_row and synthesizer_row.get("kanban_done")), "gate_ok": syn_gate} if synthesizer_row else None,
        report_ready=report_ready,
        pipeline_artifacts_ok=pipeline_artifacts_ok,
    )

    return {
        "phase": phase,
        "run_prefix": detect_run_prefix(rows),
        "board_empty": len(digest_rows) == 0,
        "status_counts": _status_counts(rows),
        "research": research_summary,
        "librarian": librarian_summary,
        "synthesizer": synthesizer_summary,
        "pipeline_artifacts_ok": pipeline_artifacts_ok,
        "report_ready": report_ready,
        "latest_report_prefix": detect_run_prefix(rows),
        "active_tasks": _active_tasks(rows),
        "board_navigation": build_board_navigation(digest_rows) if digest_rows else None,
    }
