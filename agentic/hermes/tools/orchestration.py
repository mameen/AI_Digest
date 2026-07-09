"""AI Digest kanban orchestration — board status and artifact gates for Concierge."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from tools.profiles import DISPLAY, LIBRARIAN, RESEARCHER, SYNTHESIZER, WORKER_GRAPH, normalize

HERMES_HOME = Path.home() / ".hermes"

LIBRARIAN_TITLE = "Librarian: merge & classify"
SYNTHESIZER_TITLE = "Synthesize digest"


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


def board_status(*, include_workspace: bool = True) -> dict[str, Any]:
    """Deterministic pipeline snapshot for Concierge STATUS — not LLM ground truth."""
    rows = kanban_list()
    digest_rows = digest_board_rows(rows)
    tasks: list[dict[str, Any]] = []

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
        if include_workspace and task_id:
            try:
                shown = kanban_show(task_id)
                task = shown.get("task") or {}
                ws = _task_workspace(task)
                entry["workspace"] = str(ws)
                if assignee in (RESEARCHER, LIBRARIAN, SYNTHESIZER):
                    entry.update(_artifact_gate(assignee, ws))
            except (RuntimeError, KeyError, json.JSONDecodeError) as exc:
                entry["workspace_error"] = str(exc)
        tasks.append(entry)

    research = [t for t in tasks if t["title"].startswith("Research:")]
    librarian = next((t for t in tasks if t["title"] == LIBRARIAN_TITLE), None)
    synthesizer = next((t for t in tasks if t["title"] == SYNTHESIZER_TITLE), None)

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

    pipeline_ready = (
        _role_summary(research)["all_pass"]
        and (librarian or {}).get("gate_ok") is True
        and (synthesizer or {}).get("gate_ok") is True
    )

    return {
        "ok": True,
        "board_empty": not digest_rows,
        "graph": WORKER_GRAPH,
        "roles": list(DISPLAY.keys()),
        "research": _role_summary(research),
        "librarian": _role_summary([librarian] if librarian else []),
        "synthesizer": _role_summary([synthesizer] if synthesizer else []),
        "pipeline_artifacts_ok": pipeline_ready,
        "tasks": tasks,
    }
