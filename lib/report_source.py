"""Report branch badges — which track produced a digest (llm_pipeline vs agentic Hermes)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from lib.paths import REPO_ROOT

REPORT_SOURCE_LLM = "llm-pipeline"
REPORT_SOURCE_HERMES = "agentic-hermes"

SOURCE_LABELS = {
    REPORT_SOURCE_LLM: "LLM Pipeline",
    REPORT_SOURCE_HERMES: "Hermes Agent",
}

DeploymentContext = Literal["llm_pipeline", "agentic_hermes", "app"]

_BADGE_FILES = {
    REPORT_SOURCE_LLM: REPO_ROOT / "docs" / "img" / "llm_pipeline" / "llm_pipeline.png",
    REPORT_SOURCE_HERMES: REPO_ROOT / "docs" / "img" / "agentic" / "hermes" / "hermes-agent.png",
}

_BADGE_HREF = {
    (REPORT_SOURCE_LLM, "llm_pipeline"): "../../docs/img/llm_pipeline/llm_pipeline.png",
    (REPORT_SOURCE_HERMES, "agentic_hermes"): "../../../docs/img/agentic/hermes/hermes-agent.png",
    (REPORT_SOURCE_LLM, "app"): "../img/report-source/llm_pipeline.png",
    (REPORT_SOURCE_HERMES, "app"): "../img/report-source/hermes-agent.png",
}


def detect_source_from_cfg(cfg: dict[str, Any]) -> str:
    root = str((cfg.get("output") or {}).get("root", "llm_pipeline"))
    if "hermes" in root or root.startswith("agentic"):
        return REPORT_SOURCE_HERMES
    return REPORT_SOURCE_LLM


def detect_context_from_reports_dir(reports_dir: Path) -> DeploymentContext:
    parts = reports_dir.resolve().parts
    if "app" in parts:
        return "app"
    if "hermes" in parts:
        return "agentic_hermes"
    return "llm_pipeline"


def badge_href(source: str, context: DeploymentContext) -> str:
    key = (source, context)
    if key not in _BADGE_HREF:
        raise ValueError(f"unknown report source/context: {source!r} / {context!r}")
    return _BADGE_HREF[key]


def detect_context_from_diagnostics_dir(diag_dir: Path) -> DeploymentContext:
    parts = diag_dir.resolve().parts
    if "app" in parts:
        return "app"
    if "hermes" in parts:
        return "agentic_hermes"
    return "llm_pipeline"


def source_from_poc_id(poc_id: str | None) -> str:
    if poc_id == "agentic_hermes":
        return REPORT_SOURCE_HERMES
    return REPORT_SOURCE_LLM


def enrich_diagnostics_with_source(report: dict[str, Any], diag_dir: Path) -> dict[str, Any]:
    """Stamp report_source* on a diagnostics JSON blob (for index + waterfall HTML)."""
    out = dict(report)
    context = detect_context_from_diagnostics_dir(diag_dir)
    prefix = str(out.get("prefix") or "")
    source = out.get("report_source") or source_from_poc_id(out.get("poc_id"))

    reports_index_candidates = [
        diag_dir.parent / "reports" / f"{prefix}.json",
        REPO_ROOT / "app" / "reports" / f"{prefix}.json",
    ]
    for digest_path in reports_index_candidates:
        if digest_path.is_file():
            digest = json.loads(digest_path.read_text(encoding="utf-8"))
            if digest.get("report_source"):
                source = str(digest["report_source"])
            break

    out["report_source"] = source
    out["report_source_label"] = SOURCE_LABELS.get(source, source)
    out["report_source_badge"] = badge_href(source, context)
    return out


def report_source_badge_html(report: dict[str, Any]) -> str:
    """Rounded branch seal for diagnostics waterfall headers."""
    import html as html_mod

    href = (report.get("report_source_badge") or "").strip()
    label = (report.get("report_source_label") or report.get("report_source") or "").strip()
    if not href or not label:
        return ""
    tip = f"Produced by {label}"
    return (
        f'<span class="report-source-seal" title="{html_mod.escape(tip)}" '
        f'aria-label="{html_mod.escape(label)} report">'
        f'<img src="{html_mod.escape(href)}" alt="{html_mod.escape(label)}" '
        f'title="{html_mod.escape(tip)}" loading="lazy"></span>'
    )


def stamp_document(
    data: dict[str, Any],
    source: str,
    context: DeploymentContext,
) -> dict[str, Any]:
    """Return *data* with report_source* fields for UI badges."""
    out = dict(data)
    out["report_source"] = source
    out["report_source_badge"] = badge_href(source, context)
    out["report_source_label"] = SOURCE_LABELS.get(source, source)
    return out


def sync_app_badge_assets(app: Path | None = None) -> Path:
    """Copy badge PNGs into ``app/img/report-source/`` for GitHub Pages."""
    import shutil

    root = app or (REPO_ROOT / "app")
    dest = root / "img" / "report-source"
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_BADGE_FILES[REPORT_SOURCE_LLM], dest / "llm_pipeline.png")
    shutil.copy2(_BADGE_FILES[REPORT_SOURCE_HERMES], dest / "hermes-agent.png")
    return dest


def stamp_json_file(
    path: Path,
    *,
    source: str,
    context: DeploymentContext,
) -> bool:
    """Stamp one digest JSON; return True if written."""
    data = json.loads(path.read_text(encoding="utf-8"))
    stamped = stamp_document(data, source, context)
    if (
        data.get("report_source") == stamped.get("report_source")
        and data.get("report_source_badge") == stamped.get("report_source_badge")
        and data.get("report_source_label") == stamped.get("report_source_label")
    ):
        return False
    path.write_text(json.dumps(stamped, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def infer_report_source(prefix: str, reports_dir: Path, data: dict[str, Any] | None = None) -> str:
    """Best-effort source when stamping mixed deploy trees."""
    ctx = detect_context_from_reports_dir(reports_dir)
    if ctx == "agentic_hermes":
        return REPORT_SOURCE_HERMES
    if ctx == "llm_pipeline":
        return REPORT_SOURCE_LLM
    if ctx == "app":
        agentic = (REPO_ROOT / "agentic" / "hermes" / "reports" / f"{prefix}.json").is_file()
        pipeline = (REPO_ROOT / "llm_pipeline" / "reports" / f"{prefix}.json").is_file()
        if agentic and not pipeline:
            return REPORT_SOURCE_HERMES
        if pipeline and not agentic:
            return REPORT_SOURCE_LLM
    if data and data.get("report_source") in (REPORT_SOURCE_LLM, REPORT_SOURCE_HERMES):
        return str(data["report_source"])
    return REPORT_SOURCE_LLM


def stamp_reports_tree(
    reports_dir: Path,
    *,
    source: str | None,
    context: DeploymentContext | None = None,
) -> int:
    """Stamp every digest JSON under *reports_dir*; return count updated."""
    from lib.deploy_app import list_deployable_prefixes

    if not reports_dir.is_dir():
        return 0
    ctx = context or detect_context_from_reports_dir(reports_dir)
    default_source = source
    if default_source is None and ctx == "llm_pipeline":
        default_source = REPORT_SOURCE_LLM
    elif default_source is None and ctx == "agentic_hermes":
        default_source = REPORT_SOURCE_HERMES

    updated = 0
    for prefix in list_deployable_prefixes(reports_dir):
        json_path = reports_dir / f"{prefix}.json"
        existing = json.loads(json_path.read_text(encoding="utf-8"))
        doc_source = default_source or infer_report_source(prefix, reports_dir, existing)
        if stamp_json_file(json_path, source=doc_source, context=ctx):
            updated += 1
    return updated
