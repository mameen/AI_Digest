"""Hermes adapters — validate/render and staged enrich vs ``llm_pipeline``.

Stage-1 ingest: import ``lib.ingest`` directly (no wrappers here).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from llm_pipeline.config import load_config
from llm_pipeline.dates import RunWindow
from llm_pipeline.enrich import enrich_digest
from llm_pipeline.grounding import collect_roots
from llm_pipeline.history import load_prior_digests
from llm_pipeline.render import render
from llm_pipeline.validate import apply_validation, validate_digest


def default_config() -> dict[str, Any]:
    """Load config.yaml — same source of truth as the staged pipeline."""
    return load_config()


def agentic_llm_config() -> dict[str, Any]:
    """Pipeline config with LLM routing from hermes_roles.yaml (4090 host, etc.)."""
    import json
    from pathlib import Path

    cfg = json.loads(json.dumps(default_config()))
    roles_path = Path(__file__).resolve().parents[1] / "admin" / "config" / "hermes_roles.yaml"
    if not roles_path.is_file():
        return cfg
    import yaml

    spec = yaml.safe_load(roles_path.read_text(encoding="utf-8")) or {}
    ollama = spec.get("ollama") or {}
    llm = cfg.setdefault("llm", {})
    if ollama.get("base_url"):
        llm["base_url"] = ollama["base_url"]
    if ollama.get("default_model"):
        llm["model"] = ollama["default_model"]
    if ollama.get("provider"):
        llm["provider"] = "ollama" if ollama["provider"] == "custom" else ollama["provider"]
    return cfg


def agentic_config() -> dict[str, Any]:
    """Agentic Hermes config — reports/diagnostics under ``agentic/hermes/``."""
    from lib.paths import AGENTIC_ROOT, REPO_ROOT

    cfg = agentic_llm_config()
    cfg.setdefault("output", {})["root"] = str(AGENTIC_ROOT.relative_to(REPO_ROOT))
    cfg.setdefault("diagnostics", {})["output_dir"] = "diagnostics"
    return cfg


def prior_context(cfg: dict[str, Any], window: RunWindow) -> list[dict[str, Any]]:
    """Load prior in-window digests for carry-forward / editorial context."""
    return load_prior_digests(cfg, window)


def run_staged_enrich(
    cfg: dict[str, Any],
    *,
    window: RunWindow,
    preflight_path: Path,
    crawl_md: list[Path],
    prior_digests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Full LLM enrich pass from a preflight skeleton — baseline for A/B comparison."""
    return enrich_digest(cfg, window, preflight_path, crawl_md, prior_digests)


def validate_and_render(
    cfg: dict[str, Any],
    prefix: str,
    digest: dict[str, Any],
    *,
    roots: set[str] | None = None,
) -> list[str]:
    """Validate, optionally fail, and render HTML — shared output path with run.py."""
    check_roots = roots if roots is not None else collect_roots(None)
    errors = validate_digest(cfg, digest, check_roots)
    apply_validation(cfg, errors)
    render(cfg, prefix, digest)
    return errors
