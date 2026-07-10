"""Post-GO assess, deploy to app/, and maintainer publish (commit/push)."""

from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from lib.deploy_app import execute_deploy, plan_deploy
from lib.paths import AGENTIC_ROOT, REPO_ROOT, WEB_ROOT
from llm_pipeline.validate import validate_digest

_PREFIX_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

Goodness = Literal["pass", "warn", "fail"]


def _reports_dir() -> Path:
    return AGENTIC_ROOT / "reports"


def _diagnostics_dir() -> Path:
    return AGENTIC_ROOT / "diagnostics"


def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def _load_index() -> dict[str, Any]:
    index_path = _reports_dir() / "index.json"
    if not index_path.is_file():
        return {"digests": [], "latest": None}
    return json.loads(index_path.read_text(encoding="utf-8"))


def digest_stats(data: dict[str, Any]) -> dict[str, Any]:
    categories = data.get("categories") or []
    cat_counts = {
        str(c.get("id")): len(c.get("stories") or [])
        for c in categories
        if c.get("id")
    }
    stories = [s for c in categories for s in (c.get("stories") or [])]
    sig5 = sum(1 for s in stories if int(s.get("significance") or 0) == 5)
    return {
        "summary": (data.get("summary") or "")[:200],
        "categories": cat_counts,
        "total": len(stories),
        "sig5": sig5,
        "category_count": len(categories),
    }


def _resolve_prefix(prefix: str | None) -> str:
    pfx = str(prefix or "").strip()
    if pfx:
        if not _PREFIX_RE.match(pfx):
            raise ValueError(f"invalid prefix: {pfx!r}")
        return pfx
    index = _load_index()
    latest = str(index.get("latest") or "").strip()
    if not latest:
        raise ValueError("no prefix given and reports/index.json has no latest")
    return latest


def _report_paths(prefix: str) -> tuple[Path, Path]:
    reports = _reports_dir()
    json_path = reports / f"{prefix}.json"
    html_path = reports / f"{prefix}.html"
    if not json_path.is_file() or not html_path.is_file():
        raise FileNotFoundError(
            f"missing report pair for {prefix} under {reports.relative_to(REPO_ROOT)}"
        )
    return json_path, html_path


def _index_entry(prefix: str) -> dict[str, Any] | None:
    for entry in _load_index().get("digests") or []:
        if str(entry.get("prefix") or "") == prefix:
            return entry
    return None


def _compare_baselines(
    current: dict[str, Any],
    *,
    compare_prefix: str | None,
) -> dict[str, Any]:
    index = _load_index()
    latest = str(compare_prefix or index.get("latest") or "").strip()
    if not latest or latest == str(current.get("filename_prefix") or ""):
        return {"baseline_prefix": None, "delta": {}}

    baseline_path = _reports_dir() / f"{latest}.json"
    if not baseline_path.is_file():
        return {
            "baseline_prefix": latest,
            "delta": {},
            "note": f"baseline {latest}.json not found",
        }

    baseline_stats = digest_stats(json.loads(baseline_path.read_text(encoding="utf-8")))
    cur_stats = digest_stats(current)
    cat_keys = sorted(set(baseline_stats["categories"]) | set(cur_stats["categories"]))
    category_deltas = {
        cid: cur_stats["categories"].get(cid, 0) - baseline_stats["categories"].get(cid, 0)
        for cid in cat_keys
    }
    return {
        "baseline_prefix": latest,
        "baseline_total": baseline_stats["total"],
        "delta_stories": cur_stats["total"] - baseline_stats["total"],
        "delta_sig5": cur_stats["sig5"] - baseline_stats["sig5"],
        "category_deltas": category_deltas,
    }


def _goodness_from_errors(errors: list[str], *, force: bool) -> Goodness:
    if force:
        return "warn"
    if not errors:
        return "pass"
    blocking = any(
        "story count" in e
        or e.startswith("missing required category")
        or e.startswith("missing summary")
        or e.startswith("ungrounded")
        for e in errors
    )
    return "fail" if blocking else "warn"


def assess_run(
    prefix: str | None = None,
    *,
    compare_prefix: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Validate a run, compare to history, return preview file:// links."""
    from tools.baseline import agentic_config, validation_roots

    pfx = _resolve_prefix(prefix)
    json_path, html_path = _report_paths(pfx)
    digest = json.loads(json_path.read_text(encoding="utf-8"))
    cfg = agentic_config()
    errors = validate_digest(cfg, digest, validation_roots(cfg, pfx))
    stats = digest_stats(digest)
    comparison = _compare_baselines(digest, compare_prefix=compare_prefix)
    goodness = _goodness_from_errors(errors, force=force)

    diag_json = _diagnostics_dir() / f"{pfx}.diagnostics.json"
    diag_html = _diagnostics_dir() / f"{pfx}.diagnostics.html"
    paths: dict[str, str] = {
        "report_html": str(html_path.resolve()),
        "report_json": str(json_path.resolve()),
        "reports_dir": str(_reports_dir().resolve()),
        "diagnostics_dir": str(_diagnostics_dir().resolve()),
    }
    if diag_html.is_file():
        paths["diagnostics_html"] = str(diag_html.resolve())
    if diag_json.is_file():
        paths["diagnostics_json"] = str(diag_json.resolve())

    preview: dict[str, str] = {
        "report_local": _file_uri(html_path),
        "report_json_local": _file_uri(json_path),
    }
    if diag_html.is_file():
        preview["diagnostics_local"] = _file_uri(diag_html)
    if diag_json.is_file():
        preview["diagnostics_json_local"] = _file_uri(diag_json)

    app_html = WEB_ROOT / "reports" / f"{pfx}.html"
    if app_html.is_file():
        preview["pages_report_local"] = _file_uri(app_html)
        preview["pages_archive_local"] = _file_uri(WEB_ROOT / "index" / "index.html")
        paths["pages_report_html"] = str(app_html.resolve())
        paths["pages_archive_html"] = str((WEB_ROOT / "index" / "index.html").resolve())

    warnings: list[str] = []
    if comparison.get("baseline_prefix"):
        yt_delta = (comparison.get("category_deltas") or {}).get("youtube")
        if yt_delta is not None and yt_delta <= -5:
            warnings.append(f"youtube dropped by {abs(yt_delta)} vs {comparison['baseline_prefix']}")
        total_delta = comparison.get("delta_stories")
        if isinstance(total_delta, int) and total_delta < -10:
            warnings.append(f"total stories down {abs(total_delta)} vs baseline")

    return {
        "ok": goodness != "fail",
        "goodness": goodness,
        "prefix": pfx,
        "validation_errors": errors,
        "warnings": warnings,
        "stats": stats,
        "index_entry": _index_entry(pfx),
        "vs_baseline": comparison,
        "preview": preview,
        "paths": paths,
        "open_hint_macos": f"open {shlex.quote(paths['report_html'])}",
        "deployed_to_app": app_html.is_file(),
    }


def deploy_to_app(
    prefix: str | None = None,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Copy agentic/hermes report artifacts into app/ (GitHub Pages surface)."""
    pfx = _resolve_prefix(prefix)
    if not force:
        assess = assess_run(pfx, force=False)
        if assess["goodness"] == "fail":
            return {
                "ok": False,
                "error": "assess_run failed — fix validation or pass force=true",
                "assess": assess,
            }

    plan = plan_deploy(
        source_kind="agentic-hermes",
        mode="one-day",
        prefix=pfx,
        dry_run=dry_run,
        repo=REPO_ROOT,
    )
    if not plan.prefixes:
        return {"ok": False, "error": f"no deployable report for prefix {pfx}"}

    manifest = execute_deploy(plan, REPO_ROOT)
    preview = {
        "pages_report_local": _file_uri(WEB_ROOT / "reports" / f"{pfx}.html"),
        "pages_archive_local": _file_uri(WEB_ROOT / "index" / "index.html"),
        "pages_diagnostics_local": _file_uri(WEB_ROOT / "diagnostics" / f"{pfx}.diagnostics.html"),
    }
    return {
        "ok": True,
        "dry_run": dry_run,
        "prefix": pfx,
        "manifest": manifest,
        "preview": preview,
    }


def _git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "git failed").strip())
    return proc


def _publish_paths(prefix: str) -> list[Path]:
    rels = [
        f"app/reports/{prefix}.json",
        f"app/reports/{prefix}.html",
        f"app/diagnostics/{prefix}.diagnostics.json",
        f"app/diagnostics/{prefix}.diagnostics.html",
        "app/deploy_manifest.json",
        "app/index.json",
        "app/index/index.json",
        "app/index/index.html",
        "app/diagnostics/index.json",
        "app/diagnostics/index.html",
        "app/reports/index.json",
        f"agentic/hermes/reports/{prefix}.json",
        f"agentic/hermes/reports/{prefix}.html",
        f"agentic/hermes/diagnostics/{prefix}.diagnostics.json",
        f"agentic/hermes/diagnostics/{prefix}.diagnostics.html",
        "agentic/hermes/reports/index.json",
        "agentic/hermes/reports/index.html",
        "agentic/hermes/diagnostics/index.json",
        "agentic/hermes/diagnostics/index.html",
    ]
    out: list[Path] = []
    for rel in rels:
        path = REPO_ROOT / rel
        if path.is_file():
            out.append(path)
    run_log = REPO_ROOT / f"app/diagnostics/{prefix}.run.log"
    if run_log.is_file():
        out.append(run_log)
    return out


def publish_run(
    prefix: str | None = None,
    *,
    commit_message: str | None = None,
    confirm_push: bool = False,
    dry_run: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Stage deploy artifacts, commit (runs pre-commit hooks), optional push."""
    pfx = _resolve_prefix(prefix)
    assess = assess_run(pfx, force=force)
    if assess["goodness"] == "fail" and not force:
        return {
            "ok": False,
            "error": "assess_run failed — not publishing",
            "assess": assess,
        }

    app_report = WEB_ROOT / "reports" / f"{pfx}.html"
    if not app_report.is_file():
        deploy = deploy_to_app(pfx, dry_run=False, force=force)
        if not deploy.get("ok"):
            return deploy

    paths = _publish_paths(pfx)
    if not paths:
        return {"ok": False, "error": f"no publishable files found for {pfx}"}

    rel_paths = [str(p.relative_to(REPO_ROOT)) for p in paths]
    msg = commit_message or f"chore(deploy): publish ORIO digest {pfx} to app/"

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "prefix": pfx,
            "assess": assess,
            "would_commit": msg,
            "would_stage": rel_paths,
            "would_push": confirm_push,
        }

    _git(["add", *rel_paths])
    status = _git(["status", "--porcelain"], check=False)
    staged_lines = [ln for ln in (status.stdout or "").splitlines() if ln.strip()]
    if not staged_lines:
        return {
            "ok": False,
            "error": "nothing to commit after git add",
            "prefix": pfx,
            "assess": assess,
        }

    commit = _git(
        ["commit", "-m", msg],
        check=False,
    )
    if commit.returncode != 0:
        combined = (commit.stderr or "") + (commit.stdout or "")
        return {
            "ok": False,
            "error": combined.strip() or "git commit failed",
            "prefix": pfx,
            "assess": assess,
            "staged": rel_paths,
        }

    sha = _git(["rev-parse", "--short", "HEAD"], check=True).stdout.strip()
    result: dict[str, Any] = {
        "ok": True,
        "prefix": pfx,
        "commit": sha,
        "message": msg,
        "staged": rel_paths,
        "assess": assess,
        "pushed": False,
    }

    if confirm_push:
        push = _git(["push", "origin", "main"], check=False)
        if push.returncode != 0:
            result["ok"] = False
            result["error"] = (push.stderr or push.stdout or "git push failed").strip()
            return result
        result["pushed"] = True
        result["pages_url"] = f"https://mameen.github.io/AI_Digest/reports/{quote(pfx)}.html"

    return result


_OPEN_TARGETS = frozenset(
    {"report", "report_json", "diagnostics", "diagnostics_json", "pages_report"}
)


def _open_target_path(prefix: str, target: str) -> Path:
    key = (target or "report").strip().lower()
    if key not in _OPEN_TARGETS:
        raise ValueError(
            f"unknown target {target!r} — use one of: {', '.join(sorted(_OPEN_TARGETS))}"
        )
    if key == "report":
        return _report_paths(prefix)[1]
    if key == "report_json":
        return _report_paths(prefix)[0]
    if key == "diagnostics":
        path = _diagnostics_dir() / f"{prefix}.diagnostics.html"
        if not path.is_file():
            raise FileNotFoundError(f"missing diagnostics HTML for {prefix}")
        return path
    if key == "diagnostics_json":
        path = _diagnostics_dir() / f"{prefix}.diagnostics.json"
        if not path.is_file():
            raise FileNotFoundError(f"missing diagnostics JSON for {prefix}")
        return path
    app_html = WEB_ROOT / "reports" / f"{prefix}.html"
    if not app_html.is_file():
        raise FileNotFoundError(
            f"missing app/reports/{prefix}.html — run digest_deploy_app first"
        )
    return app_html


def _platform_open_command(path: Path) -> list[str] | None:
    """Return argv for opening a local file — no shell."""
    import platform
    import shutil

    resolved = path.resolve()
    system = platform.system()
    if system == "Darwin":
        return ["open", str(resolved)]
    if system == "Linux":
        opener = shutil.which("xdg-open")
        if opener:
            return [opener, str(resolved)]
    return None


def open_report(
    prefix: str | None = None,
    *,
    target: str = "report",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Open a digest artifact in the default app (macOS ``open``, Linux ``xdg-open``)."""
    pfx = _resolve_prefix(prefix)
    path = _open_target_path(pfx, target)
    resolved = path.resolve()
    cmd = _platform_open_command(path)
    payload: dict[str, Any] = {
        "ok": False,
        "prefix": pfx,
        "target": target.strip().lower() if target else "report",
        "path": str(resolved),
        "file_uri": _file_uri(path),
    }
    if cmd is None:
        payload["error"] = "no platform opener (use path or file_uri manually)"
        payload["open_hint_macos"] = f"open {shlex.quote(str(resolved))}"
        return payload
    payload["command"] = cmd
    if dry_run:
        payload["ok"] = True
        payload["dry_run"] = True
        return payload
    proc = subprocess.run(cmd, capture_output=True, text=True)
    payload["ok"] = proc.returncode == 0
    if proc.returncode != 0:
        payload["error"] = (proc.stderr or proc.stdout or "open failed").strip()
    return payload
