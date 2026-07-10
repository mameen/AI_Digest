"""Batch digest pipeline for ``go --pipeline`` — ``run.py`` parity, not default GO."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_pipeline.dates import RunWindow, build_run_window
from llm_pipeline.diagnostics import finish_collector, get_collector, init_collector, log
from llm_pipeline.enrich import enrich_digest
from llm_pipeline.grounding import collect_roots
from llm_pipeline.history import load_prior_digests
from llm_pipeline.paths import cache_dir, diagnostics_dir, reports_dir
from llm_pipeline.validate import apply_validation, validate_digest

from tools.baseline import agentic_config, validate_and_render


def default_history_days(cfg: dict[str, Any]) -> int:
    return int((cfg.get("run") or {}).get("history_days", 10))


def resolve_go_window(
    *,
    start: str | None = None,
    history: int | None = None,
    prefix: str | None = None,
    cfg: dict[str, Any] | None = None,
) -> tuple[RunWindow, str]:
    """Digest date window + run prefix (explicit prefix wins over noon UTC default)."""
    cfg = cfg or agentic_config()
    hist = history if history is not None else default_history_days(cfg)
    window = build_run_window(start, hist)
    run_prefix = (prefix or "").strip() or window.prefix
    return window, run_prefix


def run_production_pipeline(
    *,
    start: str | None = None,
    history: int | None = None,
    prefix: str | None = None,
    fetch_only: bool = False,
    skeleton_only: bool = False,
    dry_run: bool = False,
    skip_doctor: bool = False,
    skip_ingest: bool = False,
    force: bool = False,
    telemetry_started: bool = False,
) -> dict[str, Any]:
    """Preflight → enrich → validate → render under ``agentic/hermes/reports/``."""
    cfg = agentic_config()
    if skeleton_only:
        cfg = {**cfg, "llm": {**cfg.get("llm", {}), "enabled": False}}

    window, run_prefix = resolve_go_window(
        start=start, history=history, prefix=prefix, cfg=cfg
    )
    out_reports = reports_dir(cfg)
    out_cache = cache_dir(cfg)
    out_diag = diagnostics_dir(cfg)

    result: dict[str, Any] = {
        "ok": False,
        "prefix": run_prefix,
        "window": window.label(),
        "history_days": window.history_days,
        "reports_dir": str(out_reports),
        "cache_dir": str(out_cache),
        "diagnostics_dir": str(out_diag),
        "mode": "pipeline",
    }

    if dry_run:
        result["ok"] = True
        result["dry_run"] = True
        return result

    doctor_cfg = (cfg.get("run") or {}).get("doctor") or {}
    if not skip_doctor and doctor_cfg.get("enabled", True):
        from llm_pipeline.doctor import run_doctor

        report = run_doctor(
            cfg,
            skeleton_only=skeleton_only,
            check_sources=doctor_cfg.get("check_sources", True),
        )
        if not report.ok and not force:
            result["error"] = "pre-run doctor found blocking issues"
            result["doctor"] = report.render_text()
            return result

    if not telemetry_started:
        init_collector(run_prefix, cfg)

    from lib.ingest.stage1 import crawl_leaderboards, fetch_structured_sources, run_preflight
    from llm_pipeline.paths import preflight_dir

    collector = get_collector()
    crawl_files: list[Path] = []

    if skip_ingest:
        preflight_path = preflight_dir(cfg) / f"preflight_{run_prefix}.json"
        if not preflight_path.is_file():
            result["error"] = f"skip-ingest: missing {preflight_path}"
            return result
        pfx = run_prefix
        crawl_root = out_cache / pfx / "crawl"
        crawl_files = sorted(crawl_root.glob("*.md")) if crawl_root.is_dir() else []
        log(f"  skip-ingest: reusing {preflight_path} ({len(crawl_files)} crawl md)")
        result["skip_ingest"] = True
    else:
        with collector.stage("ingestion.preflight", "Preflight"):
            pfx, preflight_path = run_preflight(cfg, run_prefix)
        log(f"  prefix={pfx} preflight={preflight_path}")

        if cfg.get("ingestion", {}).get("crawl4ai", {}).get("enabled"):
            with collector.stage("ingestion.crawl4ai", "Crawl4AI", critical=False):
                crawl_files = crawl_leaderboards(cfg, pfx, preflight_path)

        if cfg.get("ingestion", {}).get("structured_sources", {}).get("enabled", True):
            with collector.stage("ingestion.structured", "Structured APIs", critical=False):
                fetch_structured_sources(cfg, pfx)

    if fetch_only:
        finish_collector(cfg)
        result["ok"] = True
        result["fetch_only"] = True
        return result

    prior = load_prior_digests(cfg, window)
    if prior:
        log(f"  prior digests in window: {len(prior)}")

    with collector.stage("enrich", "LLM enrich"):
        digest = enrich_digest(cfg, window, preflight_path, crawl_files, prior)

    with collector.stage("validate", "Validate"):
        skeleton = json.loads(preflight_path.read_text(encoding="utf-8"))
        roots = collect_roots(skeleton.get("requires_web_fetch"))
        errors = validate_digest(cfg, digest, roots=roots)
        apply_validation(cfg, errors)

    with collector.stage("render", "Render"):
        render_errors = validate_and_render(cfg, run_prefix, digest, roots=roots)
        if render_errors:
            result["validation_notes"] = render_errors[:10]

    html_path = out_reports / f"{run_prefix}.html"
    result["report_html"] = str(html_path)
    result["story_count"] = sum(
        len(c.get("stories") or []) for c in digest.get("categories") or []
    )
    result["ok"] = html_path.is_file()
    if not result["ok"]:
        result["error"] = f"render did not produce {html_path.name}"

    diag_path = None
    try:
        diag_path = finish_collector(cfg)
    except Exception as exc:
        result["diagnostics_error"] = str(exc)
        result["ok"] = False
        result["error"] = f"finish_collector failed: {exc}"
    if diag_path:
        result["diagnostics_json"] = str(diag_path)

    return result
