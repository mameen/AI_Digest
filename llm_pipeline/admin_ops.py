"""Local admin operations: git, precheck, pipeline jobs, digest lifecycle."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from lib.paths import LLM_PIPELINE_ROOT, REPO_ROOT

REPO = REPO_ROOT
CONFIG_PATH = LLM_PIPELINE_ROOT / "config.yaml"
BRIEF_PATH = LLM_PIPELINE_ROOT / "editorial_brief.md"
CONFIG_HEADER = (
    "# AI Digest pipeline configuration\n"
    "# Local LLM via Ollama (default). Copy .env.example → .env only if you add cloud keys.\n\n"
)
PREFIX_RE = re.compile(r"^\d{14}$")

TUNING_SECTIONS: dict[str, dict[str, Any]] = {
    "pipeline": {
        "label": "Pipeline & ingest",
        "hint": "Run window, doctor, output dirs, crawl4ai, structured sources.",
        "keys": ("run", "output", "diagnostics", "ingestion"),
    },
    "enrich": {
        "label": "Enrich & LLM",
        "hint": "Model, batch sizes, category targets, tool loop, carry-forward.",
        "keys": ("llm", "enrich"),
    },
    "publish": {
        "label": "Validation & site",
        "hint": "Story minimums, required categories, render flags, footer links.",
        "keys": ("validation", "render", "site"),
    },
}


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    OK = "ok"
    FAIL = "fail"


class PipelineMode(str, Enum):
    FULL = "full"
    FETCH_ONLY = "fetch-only"
    SKELETON_ONLY = "skeleton-only"
    RENDER_ONLY = "render-only"
    ARCHIVES_ONLY = "archives-only"


@dataclass
class Job:
    id: str
    kind: str
    label: str
    state: JobState = JobState.QUEUED
    log: list[str] = field(default_factory=list)
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "state": self.state.value,
            "log": self.log[-400:],
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
        }


_jobs: dict[str, Job] = {}
_jobs_lock = threading.Lock()
_precheck_result: dict[str, Any] | None = None
_precheck_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=check,
    )


def git_status() -> dict[str, Any]:
    branch = _run_git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    dirty = bool(_run_git("status", "--porcelain").stdout.strip())
    ahead = behind = 0
    tracking = _run_git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)
    if tracking.returncode == 0:
        ab = _run_git("rev-list", "--left-right", "--count", "HEAD...@{u}", check=False)
        if ab.returncode == 0:
            parts = ab.stdout.strip().split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])
    return {
        "branch": branch,
        "dirty": dirty,
        "ahead": ahead,
        "behind": behind,
        "on_main": branch == "main",
        "can_tune": branch != "main",
        "safe_to_tune": branch != "main" or not dirty,
    }


def tuning_branch_name() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"tune/{stamp}"


def create_tuning_branch(name: str | None = None) -> dict[str, Any]:
    status = git_status()
    if status["branch"] != "main":
        return {"ok": True, "branch": status["branch"], "created": False, "message": "Already on a branch."}
    branch = (name or tuning_branch_name()).strip()
    if not branch or branch == "main":
        raise ValueError("Invalid branch name")
    _run_git("checkout", "-b", branch)
    return {"ok": True, "branch": branch, "created": True}


def git_commit(message: str) -> dict[str, Any]:
    msg = message.strip()
    if not msg:
        raise ValueError("Commit message required")
    _run_git("add", "-A")
    proc = _run_git("commit", "-m", msg, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "commit failed")
    return {"ok": True, "sha": _run_git("rev-parse", "--short", "HEAD").stdout.strip()}


def git_push(set_upstream: bool = True) -> dict[str, Any]:
    branch = git_status()["branch"]
    args = ["push"]
    if set_upstream:
        args = ["push", "-u", "origin", branch]
    proc = _run_git(*args, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "push failed")
    return {"ok": True, "branch": branch}


def git_merge_main() -> dict[str, Any]:
    status = git_status()
    if status["branch"] == "main":
        raise ValueError("Already on main — pull or push instead.")
    if status["dirty"]:
        raise ValueError("Working tree dirty — commit or stash before merging.")
    branch = status["branch"]
    _run_git("checkout", "main")
    _run_git("pull", "--ff-only", check=False)
    _run_git("merge", "--no-ff", branch, "-m", f"Merge branch '{branch}'")
    return {"ok": True, "merged": branch}


def _load_config_dict() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _dump_config(data: dict[str, Any]) -> str:
    body = yaml.dump(
        data,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )
    return CONFIG_HEADER + body


def _section_yaml(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    section = {k: data[k] for k in keys if k in data}
    return yaml.dump(
        section,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=120,
    )


def _require_tuning_branch(force_branch: bool = False) -> dict[str, Any]:
    status = git_status()
    if status["on_main"] and not force_branch:
        raise PermissionError(
            "Tuning is locked on main. Create a tuning branch first "
            f"(suggested: {tuning_branch_name()})."
        )
    return status


def read_config_bundle() -> dict[str, Any]:
    data = _load_config_dict()
    return {
        "config_yaml": CONFIG_PATH.read_text(encoding="utf-8"),
        "config_sections": {
            sid: _section_yaml(data, meta["keys"]) for sid, meta in TUNING_SECTIONS.items()
        },
        "tuning_sections": {
            sid: {"label": meta["label"], "hint": meta["hint"]} for sid, meta in TUNING_SECTIONS.items()
        },
        "editorial_brief": BRIEF_PATH.read_text(encoding="utf-8"),
    }


def write_config_bundle(
    *,
    config_yaml: str | None = None,
    config_section: str | None = None,
    section_yaml: str | None = None,
    editorial_brief: str | None = None,
    force_branch: bool = False,
) -> dict[str, Any]:
    status = _require_tuning_branch(force_branch)
    written: list[str] = []

    if config_section is not None or section_yaml is not None:
        if not config_section or section_yaml is None:
            raise ValueError("config_section and section_yaml must be supplied together")
        meta = TUNING_SECTIONS.get(config_section)
        if not meta:
            raise ValueError(f"Unknown config section: {config_section!r}")
        patch = yaml.safe_load(section_yaml) or {}
        if not isinstance(patch, dict):
            raise ValueError("Section YAML must be a mapping")
        allowed = set(meta["keys"])
        unexpected = set(patch) - allowed
        if unexpected:
            raise ValueError(f"Unexpected keys in section: {', '.join(sorted(unexpected))}")
        data = _load_config_dict()
        for key in allowed:
            if key in patch:
                data[key] = patch[key]
        CONFIG_PATH.write_text(_dump_config(data), encoding="utf-8")
        written.append("llm_pipeline/config.yaml")
    elif config_yaml is not None:
        CONFIG_PATH.write_text(config_yaml, encoding="utf-8")
        written.append("llm_pipeline/config.yaml")

    if editorial_brief is not None:
        BRIEF_PATH.write_text(editorial_brief, encoding="utf-8")
        written.append("llm_pipeline/editorial_brief.md")

    if not written:
        raise ValueError("Nothing to write")

    return {"ok": True, "written": written, "branch": status["branch"]}


def list_digests(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    from llm_pipeline.paths import diagnostics_dir, reports_dir

    index_path = reports_dir(cfg) / "index.json"
    if not index_path.is_file():
        return []
    data = json.loads(index_path.read_text(encoding="utf-8"))
    diag_dir = diagnostics_dir(cfg)
    out: list[dict[str, Any]] = []
    for item in data.get("digests") or []:
        prefix = item.get("prefix") or ""
        out.append(
            {
                **item,
                "has_html": (reports_dir(cfg) / f"{prefix}.html").is_file(),
                "has_json": (reports_dir(cfg) / f"{prefix}.json").is_file(),
                "has_diagnostics": (diag_dir / f"{prefix}.diagnostics.json").is_file(),
            }
        )
    return out


def _validate_prefix(prefix: str) -> str:
    p = prefix.strip()
    if not PREFIX_RE.match(p):
        raise ValueError(f"Invalid prefix: {prefix!r}")
    return p


def delete_digest(cfg: dict[str, Any], prefix: str) -> dict[str, Any]:
    from llm_pipeline.paths import cache_dir, diagnostics_dir, preflight_dir, reports_dir

    pfx = _validate_prefix(prefix)
    removed: list[str] = []
    for base, pattern in (
        (reports_dir(cfg), f"{pfx}.*"),
        (diagnostics_dir(cfg), f"{pfx}.diagnostics.*"),
        (preflight_dir(cfg), f"preflight_{pfx}.json"),
        (cache_dir(cfg), f"{pfx}_*"),
        (cache_dir(cfg) / pfx, "*"),
    ):
        if base.is_dir():
            for path in base.glob(pattern):
                if path.is_file():
                    path.unlink()
                    removed.append(str(path.relative_to(REPO)))
                elif path.is_dir():
                    import shutil

                    shutil.rmtree(path)
                    removed.append(str(path.relative_to(REPO)))
    cache_sub = cache_dir(cfg) / pfx
    if cache_sub.is_dir():
        import shutil

        shutil.rmtree(cache_sub)
        removed.append(str(cache_sub.relative_to(REPO)))
    return {"ok": True, "prefix": pfx, "removed": removed}


def run_precheck() -> dict[str, Any]:
    global _precheck_result
    log: list[str] = []
    ok = True

    proc = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "pipeline", "tests", "vendor/ai-news-digest/scripts"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    log.append("compileall: " + ("OK" if proc.returncode == 0 else "FAIL"))
    if proc.stderr:
        log.append(proc.stderr.strip()[-2000:])
    ok = ok and proc.returncode == 0

    proc = subprocess.run(
        [sys.executable, "run_tests.py"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    tail = (proc.stdout or "") + (proc.stderr or "")
    log.append("run_tests.py: " + ("OK" if proc.returncode == 0 else "FAIL"))
    if tail:
        log.append(tail.strip()[-8000:])
    ok = ok and proc.returncode == 0

    result = {"ok": ok, "finished_at": _now(), "log": log}
    with _precheck_lock:
        _precheck_result = result
    return result


def precheck_latest() -> dict[str, Any] | None:
    with _precheck_lock:
        return dict(_precheck_result) if _precheck_result else None


def _append(job: Job, line: str) -> None:
    job.log.append(line.rstrip())


def _spawn_job(kind: str, label: str, argv: list[str]) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], kind=kind, label=label)
    with _jobs_lock:
        _jobs[job.id] = job

    def runner() -> None:
        job.state = JobState.RUNNING
        job.started_at = _now()
        _append(job, f"$ {' '.join(argv)}")
        try:
            proc = subprocess.Popen(
                argv,
                cwd=REPO,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            assert proc.stdout is not None
            for line in proc.stdout:
                _append(job, line.rstrip())
            proc.wait()
            job.exit_code = proc.returncode
            job.state = JobState.OK if proc.returncode == 0 else JobState.FAIL
        except Exception as exc:
            _append(job, f"ERROR: {exc}")
            job.state = JobState.FAIL
            job.exit_code = 1
        job.finished_at = _now()

    threading.Thread(target=runner, daemon=True).start()
    return job


def start_pipeline(
    cfg: dict[str, Any],
    *,
    mode: PipelineMode,
    start: str | None = None,
    history: int = 10,
    prefix: str | None = None,
) -> Job:
    py = sys.executable
    if mode == PipelineMode.FULL:
        argv = [py, "run.py", "--history", str(history)]
        if start:
            argv.extend(["--start", start])
        return _spawn_job("pipeline", f"Full pipeline {start or 'today'}", argv)
    if mode == PipelineMode.FETCH_ONLY:
        argv = [py, "run.py", "--fetch-only", "--history", str(history)]
        if start:
            argv.extend(["--start", start])
        return _spawn_job("pipeline", "Fetch-only ingest", argv)
    if mode == PipelineMode.SKELETON_ONLY:
        argv = [py, "run.py", "--skeleton-only", "--history", str(history)]
        if start:
            argv.extend(["--start", start])
        return _spawn_job("pipeline", "Skeleton-only promote", argv)
    if mode == PipelineMode.RENDER_ONLY:
        pfx = _validate_prefix(prefix or "")
        script = (
            "import json; from llm_pipeline.config import load_config; from llm_pipeline.render import render; "
            f"cfg=load_config(); p='{pfx}'; "
            "render(cfg, p, json.load(open('reports/'+p+'.json', encoding='utf-8')))"
        )
        return _spawn_job("render", f"Render-only {pfx}", [py, "-c", script])
    if mode == PipelineMode.ARCHIVES_ONLY:
        script = (
            "from llm_pipeline.config import load_config; from llm_pipeline.render import rebuild_reports_archive; "
            "from llm_pipeline.paths import diagnostics_dir; "
            "from llm_pipeline.diagnostics_frame import rebuild_diagnostics_archive; "
            "from llm_pipeline.diagnostics import rebuild_diagnostics_waterfall_pages; "
            "from llm_pipeline.admin_frame import rebuild_admin_archive; "
            "cfg=load_config(); rebuild_reports_archive(cfg); "
            "d=diagnostics_dir(cfg); rebuild_diagnostics_waterfall_pages(d); "
            "rebuild_diagnostics_archive(d, cfg); rebuild_admin_archive(cfg)"
        )
        return _spawn_job("archives", "Frontend archives rebuild", [py, "-c", script])
    raise ValueError(f"Unknown mode: {mode}")


def list_jobs() -> list[dict[str, Any]]:
    with _jobs_lock:
        return [j.to_dict() for j in sorted(_jobs.values(), key=lambda x: x.started_at or "", reverse=True)]


def get_job(job_id: str) -> dict[str, Any] | None:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return job.to_dict() if job else None
