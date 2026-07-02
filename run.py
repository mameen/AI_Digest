#!/usr/bin/env python3
"""
AI Digest: one-command daily pipeline (no UI).

Usage:
    python run.py                              # today, 10-day lookback
    python run.py --start 2026-06-27           # digest date (default: today UTC)
    python run.py --history 14                 # editorial lookback in days
    python run.py --fetch-only                 # preflight + optional crawl4ai only
    python run.py --skeleton-only              # skip LLM enrich
    python run.py --dry-run                    # print paths only
    python run.py --doctor                     # run the pre-run self-check and exit
    python run.py --skip-doctor                # skip the pre-run self-check

Outputs land under ``reports/``, ``diagnostics/``, and ``.cache/``.
See README.md for setup (Ollama, Playwright, yt-dlp).
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.config import load_config
from pipeline.dates import build_run_window
from pipeline.diagnostics import finish_collector, init_collector, log
from pipeline.doctor import run_doctor
from pipeline.enrich import enrich_digest
from pipeline.fetch import crawl_leaderboards, fetch_structured_sources, run_preflight
from pipeline.grounding import collect_roots
from pipeline.history import load_prior_digests
from pipeline.paths import cache_dir, diagnostics_dir, reports_dir
from pipeline.render import render
from pipeline.validate import apply_validation, validate_digest


def main() -> None:
    cfg = load_config()
    default_history = int(cfg.get("run", {}).get("history_days", 10))

    parser = argparse.ArgumentParser(description="AI Digest daily pipeline runner")
    parser.add_argument("--start", metavar="DATE", help="Digest date YYYY-MM-DD or YYYYMMDD")
    parser.add_argument(
        "--history",
        type=int,
        metavar="N",
        default=default_history,
        help=f"Editorial lookback in days (default: {default_history})",
    )
    parser.add_argument("--fetch-only", action="store_true", help="Stop after ingestion")
    parser.add_argument("--skeleton-only", action="store_true", help="Skip LLM enrich")
    parser.add_argument("--dry-run", action="store_true", help="Show paths only")
    parser.add_argument("--doctor", action="store_true",
                        help="Run the pre-run self-check and exit")
    parser.add_argument("--skip-doctor", action="store_true",
                        help="Skip the pre-run self-check")
    parser.add_argument("--force", action="store_true",
                        help="Proceed even if the self-check reports blocking failures")
    args = parser.parse_args()

    try:
        window = build_run_window(args.start, args.history)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    reports = reports_dir(cfg)
    cache = cache_dir(cfg)
    diag = diagnostics_dir(cfg)

    print(f"Reports:     {reports}")
    print(f"Cache:       {cache}")
    if cfg.get("diagnostics", {}).get("enabled", True):
        print(f"Diagnostics: {diag}")
    print(f"Run window:  {window.label()}  prefix={window.prefix}")
    if cfg.get("llm", {}).get("enabled") and not args.skeleton_only:
        llm = cfg["llm"]
        print(f"LLM:         local Ollama {llm.get('model')} @ {llm.get('base_url')}")

    if args.dry_run:
        return

    doctor_cfg = (cfg.get("run") or {}).get("doctor") or {}
    if args.doctor or (doctor_cfg.get("enabled", True) and not args.skip_doctor):
        print("\n[0/4] Pre-run self-check")
        report = run_doctor(
            cfg,
            skeleton_only=args.skeleton_only,
            check_sources=doctor_cfg.get("check_sources", True),
        )
        print(report.render_text())
        if args.doctor:
            raise SystemExit(0 if report.ok else 2)
        if not report.ok and not args.force:
            raise SystemExit(
                "\nPre-run self-check found blocking issues (see above).\n"
                "  Fix them, or re-run with --force to proceed anyway."
            )

    if args.skeleton_only:
        cfg = {**cfg, "llm": {**cfg.get("llm", {}), "enabled": False}}

    collector = init_collector(window.prefix, cfg)

    log("\n[1/4] Ingestion: preflight")
    if not cfg.get("ingestion", {}).get("preflight", True):
        raise SystemExit("preflight disabled in config")
    with collector.stage("ingestion.preflight", "Preflight"):
        prefix, preflight_path = run_preflight(cfg, window.prefix)
    log(f"  prefix={prefix} preflight={preflight_path}")

    crawl_files: list[Path] = []
    if cfg.get("ingestion", {}).get("crawl4ai", {}).get("enabled"):
        log("\n[1b] Ingestion: Crawl4AI")
        with collector.stage("ingestion.crawl4ai", "Crawl4AI", critical=False):
            crawl_files = crawl_leaderboards(cfg, prefix, preflight_path)

    if cfg.get("ingestion", {}).get("structured_sources", {}).get("enabled", True):
        log("\n[1c] Ingestion: structured APIs")
        with collector.stage("ingestion.structured", "Structured APIs", critical=False):
            fetch_structured_sources(cfg, prefix)

    if args.fetch_only:
        finish_collector(cfg)
        print("\nDone (--fetch-only).")
        return

    prior = load_prior_digests(cfg, window)
    if prior:
        log(f"  prior digests in window: {len(prior)}")

    log("\n[2/4] Enrich: multi-pass LLM")
    with collector.stage("enrich", "LLM enrich"):
        digest = enrich_digest(cfg, window, preflight_path, crawl_files, prior)

    log("\n[3/4] Validate")
    with collector.stage("validate", "Validate"):
        skeleton = json.loads(preflight_path.read_text(encoding="utf-8"))
        roots = collect_roots(skeleton.get("requires_web_fetch"))
        errors = validate_digest(cfg, digest, roots=roots)
        apply_validation(cfg, errors)

    log("\n[4/4] Render: HTML + archive index")
    with collector.stage("render", "Render"):
        render(cfg, prefix, digest)

    diag_path = finish_collector(cfg)

    print("\nDone.")
    print(f"  archive: {reports / 'index.html'}")
    print(f"  digest:  {reports / f'{prefix}.html'}")
    if diag_path:
        print(f"  diagnostics archive: {diag_path.parent / 'index.html'}")
        print(f"  diagnostics run:     {diag_path.with_suffix('.html')}")

    if cfg.get("render", {}).get("open_browser"):
        webbrowser.open((reports / f"{prefix}.html").as_uri())


if __name__ == "__main__":
    main()
