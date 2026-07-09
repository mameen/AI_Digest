"""Copy digest artifacts from pipeline or agentic sources into ``app/``."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from lib.paths import REPO_ROOT

SourceKind = Literal["pipeline", "agentic-hermes"]

_PREFIX_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


@dataclass(frozen=True)
class DeploySource:
    kind: SourceKind
    reports: Path
    diagnostics: Path

    def label(self, repo: Path | None = None) -> str:
        """Repo-relative path to the source tree (no absolute home paths in manifests)."""
        root = repo or REPO_ROOT
        try:
            return self.reports.parent.relative_to(root).as_posix()
        except ValueError:
            return self.reports.parent.as_posix()


@dataclass
class DeployPlan:
    source: DeploySource
    prefixes: list[str]
    dry_run: bool
    dest_reports: Path
    dest_diagnostics: Path
    dest_index: Path
    copies: list[tuple[Path, Path]]


def app_root(repo: Path | None = None) -> Path:
    return (repo or REPO_ROOT) / "app"


def resolve_source(kind: SourceKind, repo: Path | None = None) -> DeploySource:
    root = repo or REPO_ROOT
    if kind == "pipeline":
        base = root / "llm_pipeline"
    else:
        base = root / "agentic" / "hermes"
    return DeploySource(kind=kind, reports=base / "reports", diagnostics=base / "diagnostics")


def list_deployable_prefixes(reports_dir: Path) -> list[str]:
    """Report prefixes that have both JSON and HTML in *reports_dir*."""
    if not reports_dir.is_dir():
        return []
    out: list[str] = []
    for json_path in sorted(reports_dir.glob("*.json")):
        if json_path.name == "index.json":
            continue
        stem = json_path.stem
        if not _PREFIX_RE.match(stem):
            continue
        if (reports_dir / f"{stem}.html").is_file():
            out.append(stem)
    return out


def prefixes_missing_from_app(source: DeploySource, repo: Path | None = None) -> list[str]:
    """Prefixes present in *source* but not yet under ``app/reports/``."""
    dest = app_reports_dir(repo)
    have = set(list_deployable_prefixes(dest))
    return [p for p in list_deployable_prefixes(source.reports) if p not in have]


def app_reports_dir(repo: Path | None = None) -> Path:
    return app_root(repo) / "reports"


def app_diagnostics_dir(repo: Path | None = None) -> Path:
    return app_root(repo) / "diagnostics"


def app_index_dir(repo: Path | None = None) -> Path:
    return app_root(repo) / "index"


def _diagnostics_files_for_prefix(diag_dir: Path, prefix: str) -> list[Path]:
    if not diag_dir.is_dir():
        return []
    out: list[Path] = []
    for pattern in (
        f"{prefix}.diagnostics.json",
        f"{prefix}.diagnostics.html",
        f"{prefix}.run.log",
    ):
        path = diag_dir / pattern
        if path.is_file():
            out.append(path)
    return out


def plan_deploy(
    *,
    source_kind: SourceKind,
    mode: Literal["auto", "one-day", "all"],
    prefix: str | None = None,
    dry_run: bool = True,
    repo: Path | None = None,
) -> DeployPlan:
    source = resolve_source(source_kind, repo)
    dest_reports = app_reports_dir(repo)
    dest_diagnostics = app_diagnostics_dir(repo)
    dest_index = app_index_dir(repo)

    if mode == "auto":
        prefixes = prefixes_missing_from_app(source, repo)
    elif mode == "all":
        prefixes = list_deployable_prefixes(source.reports)
    else:
        if not prefix:
            raise ValueError("one-day mode requires a run prefix")
        if not _PREFIX_RE.match(prefix):
            raise ValueError(f"invalid prefix: {prefix!r}")
        json_path = source.reports / f"{prefix}.json"
        html_path = source.reports / f"{prefix}.html"
        if not json_path.is_file() or not html_path.is_file():
            raise FileNotFoundError(
                f"missing report pair in {source.reports}: {prefix}.json + {prefix}.html"
            )
        prefixes = [prefix]

    copies: list[tuple[Path, Path]] = []
    for pfx in prefixes:
        copies.append((source.reports / f"{pfx}.json", dest_reports / f"{pfx}.json"))
        copies.append((source.reports / f"{pfx}.html", dest_reports / f"{pfx}.html"))
        for src in _diagnostics_files_for_prefix(source.diagnostics, pfx):
            copies.append((src, dest_diagnostics / src.name))

    return DeployPlan(
        source=source,
        prefixes=prefixes,
        dry_run=dry_run,
        dest_reports=dest_reports,
        dest_diagnostics=dest_diagnostics,
        dest_index=dest_index,
        copies=copies,
    )


def _build_app_reports_index(reports_dir: Path) -> dict:
    """Like ``build_index`` but includes every digest JSON/HTML pair (not only 14-digit)."""
    _ensure_scripts_path()
    from _report_utils import digest_index_entry  # type: ignore

    entries: list[dict] = []
    by_date: dict[str, dict] = {}
    for stem in list_deployable_prefixes(reports_dir):
        path = reports_dir / f"{stem}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = digest_index_entry(data, stem)
        entries.append(entry)
        prev = by_date.get(entry["date"])
        if not prev or entry["prefix"] > prev["prefix"]:
            by_date[entry["date"]] = entry
    entries.sort(key=lambda e: e["prefix"])
    latest = entries[-1]["prefix"] if entries else None
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latest": latest,
        "digests": entries,
        "by_date": list(by_date.values()),
    }


def _ensure_scripts_path() -> None:
    import sys

    scripts = REPO_ROOT / "llm_pipeline" / "vendor" / "ai-news-digest" / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))


def _write_reports_index_redirect(reports_dir: Path) -> None:
    """Keep ``/reports/`` bookmarks working; archive lives under ``/index/``."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "index.html").write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=../index/index.html">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Digest — archive</title>
  <link rel="canonical" href="../index/index.html">
</head>
<body>
  <p>Redirecting to the <a href="../index/index.html">digest archive</a>…</p>
</body>
</html>
""",
        encoding="utf-8",
    )


def _sync_app_author_photo(app: Path, cfg: dict[str, Any], repo: Path | None = None) -> bool:
    """Copy the configured author headshot into ``app/assets/`` for archive frames."""
    from llm_pipeline.frame_author import sync_author_assets

    fake_reports = app / "reports"
    fake_reports.mkdir(parents=True, exist_ok=True)
    return sync_author_assets(fake_reports, cfg, repo=repo)


def rebuild_app_archives(repo: Path | None = None, *, dry_run: bool = False) -> None:
    """Rebuild ``app/index/`` and ``app/diagnostics/`` archive frames from deployed files."""
    if dry_run:
        return

    root = app_root(repo)
    reports = app_reports_dir(repo)
    index_dir = app_index_dir(repo)
    diag_dir = app_diagnostics_dir(repo)
    index_dir.mkdir(parents=True, exist_ok=True)
    _write_reports_index_redirect(reports)

    _ensure_scripts_path()
    from _report_utils import build_frame_html  # type: ignore

    from llm_pipeline.config import load_config
    from llm_pipeline.diagnostics import rebuild_diagnostics_waterfall_pages
    from llm_pipeline.diagnostics_frame import rebuild_diagnostics_archive
    from llm_pipeline.frame_author import inject_author_card
    from llm_pipeline.frame_nav import admin_nav_enabled, diagnostics_available, inject_frame_nav
    from llm_pipeline.frame_html import assert_archive_html_ready
    from llm_pipeline.site_footer import inject_site_footer

    cfg = load_config()
    has_author_photo = _sync_app_author_photo(root, cfg, repo)
    index = _build_app_reports_index(reports)
    index_blob = json.dumps(index, indent=2, ensure_ascii=False) + "\n"
    (root / "index.json").write_text(index_blob, encoding="utf-8")
    (reports / "index.json").write_text(index_blob, encoding="utf-8")
    (index_dir / "index.json").write_text(index_blob, encoding="utf-8")

    frame = build_frame_html(reports_dir=reports)
    frame = inject_author_card(
        frame,
        cfg,
        assets_prefix="../assets" if has_author_photo else None,
    )
    frame = inject_frame_nav(
        frame,
        "reports",
        diagnostics_available=diagnostics_available(cfg, diag_dir),
        admin_available=False,
    )
    frame = inject_site_footer(frame, cfg)
    assert_archive_html_ready(frame)
    (index_dir / "index.html").write_text(frame, encoding="utf-8")

    if any(diag_dir.glob("*.diagnostics.json")):
        rebuild_diagnostics_waterfall_pages(diag_dir, cfg)
        rebuild_diagnostics_archive(diag_dir, cfg)
        diag_frame = (diag_dir / "index.html").read_text(encoding="utf-8")
        diag_frame = diag_frame.replace('href="../reports/index.html"', 'href="../index/index.html"')
        (diag_dir / "index.html").write_text(diag_frame, encoding="utf-8")

    root_index = root / "index.html"
    root_index.write_text(
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=index/index.html">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Digest</title>
  <link rel="canonical" href="index/index.html">
</head>
<body>
  <p>Redirecting to the <a href="index/index.html">digest archive</a>…</p>
  <p>Diagnostics: <a href="diagnostics/index.html">diagnostics/index.html</a></p>
</body>
</html>
""",
        encoding="utf-8",
    )


def execute_deploy(plan: DeployPlan, repo: Path | None = None) -> dict:
    """Run *plan*; return manifest dict."""
    root = repo or REPO_ROOT
    app = app_root(root)
    manifest: dict = {
        "deployed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": plan.source.label(root),
        "source_kind": plan.source.kind,
        "prefixes": plan.prefixes,
        "dry_run": plan.dry_run,
        "files": [],
    }

    if not plan.prefixes:
        return manifest

    if plan.dry_run:
        manifest["files"] = [
            {"from": str(src.relative_to(root)), "to": str(dest.relative_to(root))}
            for src, dest in plan.copies
        ]
        return manifest

    plan.dest_reports.mkdir(parents=True, exist_ok=True)
    plan.dest_diagnostics.mkdir(parents=True, exist_ok=True)
    plan.dest_index.mkdir(parents=True, exist_ok=True)

    for src, dest in plan.copies:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        manifest["files"].append(
            {"from": str(src.relative_to(root)), "to": str(dest.relative_to(root))}
        )

    from lib.report_source import (
        REPORT_SOURCE_HERMES,
        REPORT_SOURCE_LLM,
        stamp_json_file,
        stamp_reports_tree,
        sync_app_badge_assets,
    )

    sync_app_badge_assets(app)
    kind_source = REPORT_SOURCE_HERMES if plan.source.kind == "agentic-hermes" else REPORT_SOURCE_LLM
    for pfx in plan.prefixes:
        stamp_json_file(plan.dest_reports / f"{pfx}.json", source=kind_source, context="app")
    stamp_reports_tree(plan.dest_reports, source=None, context="app")

    rebuild_app_archives(root, dry_run=False)
    manifest_path = app / "deploy_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
