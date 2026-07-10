"""AI Digest kanban orchestration — board status and artifact gates for Concierge."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from tools.profiles import (
    DISPLAY,
    LIBRARIAN,
    LOGICAL_ROLES,
    RESEARCHER,
    SYNTHESIZER,
    WORKER_GRAPH,
    normalize,
)

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
    return json.loads(proc.stdout)


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
    return json.loads(proc.stdout)


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
    from tools.artifacts import (
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
) -> str:
    """Coarse pipeline phase for Concierge STATUS (not LLM judgment)."""
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
    if not lib_done:
        return "librarian"
    if not syn_done:
        return "synthesizer"
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
        "render": "awaiting validate/render",
        "complete": "report ready",
    }
    lines.append(f"Pipeline phase: {phase_labels.get(phase, phase)}")

    if payload.get("report_ready"):
        lines.append(f"Report HTML: {payload.get('report_html')}")
    elif prefix and phase == "render":
        lines.append("Workers finished — GO may still be rendering or assess not run yet.")

    active = payload.get("active_tasks") or []
    if active:
        lines.append("Active / next up:")
        for row in active:
            lines.append(f"  - [{row.get('status')}] {row.get('title')} ({row.get('assignee')})")

    nav = payload.get("board_navigation") or {}
    if nav:
        lines.append("Kanban find (repost these ids in chat):")
        primary = nav.get("primary_anchor")
        if isinstance(primary, dict) and primary.get("id"):
            lines.append(
                f"  Primary: {primary['id']} — {primary['title']} [{primary['status']}]"
            )
            if primary.get("kanban_show"):
                lines.append(f"  Drill: {primary['kanban_show']}")
        librarian_ref = nav.get("librarian")
        if (
            isinstance(librarian_ref, dict)
            and librarian_ref.get("id")
            and librarian_ref.get("id") != (primary or {}).get("id")
        ):
            lines.append(
                f"  Librarian: {librarian_ref['id']} — {librarian_ref['title']} "
                f"[{librarian_ref['status']}]"
            )
        synthesizer_ref = nav.get("synthesizer")
        if isinstance(synthesizer_ref, dict) and synthesizer_ref.get("id"):
            lines.append(
                f"  Synthesizer: {synthesizer_ref['id']} — {synthesizer_ref['title']} "
                f"[{synthesizer_ref['status']}]"
            )
        roots = nav.get("root_tasks") or []
        if roots:
            lines.append(f"  Root research tasks ({len(roots)}):")
            pending = [r for r in roots if r.get("status") != "done"]
            done = [r for r in roots if r.get("status") == "done"]
            for ref in (pending + done)[:8]:
                lines.append(f"    {ref['id']} {ref['title']} [{ref['status']}]")
            if len(roots) > 8:
                lines.append(f"    … and {len(roots) - 8} more (see root_tasks in JSON)")
        list_cmd = str(nav.get("list_cmd") or "").strip()
        if list_cmd:
            lines.append(f"  List all: {list_cmd}")

    return lines


def _latest_report_prefix() -> str | None:
    from lib.paths import AGENTIC_ROOT

    index_path = AGENTIC_ROOT / "reports" / "index.json"
    if not index_path.is_file():
        return None
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    latest = str(data.get("latest") or "").strip()
    return latest or None


def board_status(*, include_workspace: bool = True, brief: bool = False) -> dict[str, Any]:
    """Deterministic pipeline snapshot for Concierge STATUS — not LLM ground truth."""
    if not _hermes_bin():
        return {
            "ok": False,
            "error": "hermes not on PATH",
            "summary": ["Hermes CLI not available — cannot read kanban board."],
        }

    rows = kanban_list(raise_on_error=True)
    digest_rows = digest_board_rows(rows)
    run_prefix = detect_run_prefix(digest_rows)
    report_ready = False
    report_html: str | None = None
    if run_prefix:
        html_path, _ = _report_paths(run_prefix)
        report_ready = html_path.is_file()
        if report_ready:
            report_html = str(html_path)

    tasks: list[dict[str, Any]] = []
    inspect_gates = include_workspace and not brief

    for row in digest_rows:
        assignee = normalize(str(row.get("assignee") or ""))
        status = str(row.get("status") or "")
        title = str(row.get("title") or "")
        task_id = str(row.get("id") or "")
        entry: dict[str, Any] = {
            "id": task_id,
            "title": title,
            "assignee": assignee,
            "role_label": DISPLAY.get(assignee, assignee),
            "status": status,
            "kanban_done": status == "done",
        }
        if inspect_gates and task_id:
            try:
                shown = kanban_show(task_id)
                task = shown.get("task") or {}
                ws = _task_workspace(task)
                entry["workspace"] = str(ws)
                summary = str(shown.get("latest_summary") or "").strip()
                if summary:
                    entry["latest_summary"] = summary[:400]
                role = normalize(assignee)
                if role in (RESEARCHER, LIBRARIAN, SYNTHESIZER):
                    entry.update(_artifact_gate(role, ws))
            except (RuntimeError, KeyError, json.JSONDecodeError) as exc:
                entry["workspace_error"] = str(exc)
        tasks.append(entry)

    research_tasks = [t for t in tasks if t["title"].startswith("Research:")]
    librarian = next((t for t in tasks if t["title"] == LIBRARIAN_TITLE), None)
    synthesizer = next((t for t in tasks if t["title"] == SYNTHESIZER_TITLE), None)

    research_summary = _role_summary(research_tasks)
    librarian_summary = _role_summary([librarian] if librarian else [])
    synthesizer_summary = _role_summary([synthesizer] if synthesizer else [])

    if brief and research_tasks:
        research_summary = {
            "count": len(research_tasks),
            "done": sum(1 for t in research_tasks if t.get("kanban_done")),
            "artifact_pass": sum(1 for t in research_tasks if t.get("gate_ok") is True),
            "all_pass": False,
        }
        if librarian:
            librarian_summary = {
                "count": 1,
                "done": int(librarian.get("kanban_done") or False),
                "artifact_pass": 0,
                "all_pass": False,
            }
        if synthesizer:
            synthesizer_summary = {
                "count": 1,
                "done": int(synthesizer.get("kanban_done") or False),
                "artifact_pass": 0,
                "all_pass": False,
            }

    pipeline_ready = (
        research_summary["all_pass"]
        and (librarian or {}).get("gate_ok") is True
        and (synthesizer or {}).get("gate_ok") is True
    )

    phase = infer_pipeline_phase(
        board_empty=not digest_rows,
        research=research_summary,
        librarian=librarian,
        synthesizer=synthesizer,
        report_ready=report_ready,
    )

    board_navigation = build_board_navigation(digest_rows)

    payload: dict[str, Any] = {
        "ok": True,
        "board_empty": not digest_rows,
        "run_prefix": run_prefix,
        "phase": phase,
        "graph": WORKER_GRAPH,
        "roles": list(LOGICAL_ROLES),
        "status_counts": _status_counts(digest_rows),
        "active_tasks": _active_tasks(digest_rows),
        "board_navigation": board_navigation,
        "research": research_summary,
        "librarian": librarian_summary,
        "synthesizer": synthesizer_summary,
        "pipeline_artifacts_ok": pipeline_ready,
        "report_ready": report_ready,
        "report_html": report_html,
        "latest_report_prefix": _latest_report_prefix(),
        "tasks": tasks,
        "brief": brief,
    }
    payload["summary"] = format_status_summary(payload)
    return payload
