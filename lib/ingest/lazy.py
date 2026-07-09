"""Lazy, idempotent stage-1 helpers — fetch on cache miss per tool call."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from llm_pipeline.leaderboards import AA_CRAWL_SLUG
from llm_pipeline.paths import cache_dir, preflight_dir

from lib.ingest.fixtures import evaluation_fixture_path, fixture_path, resolve_fixture
from lib.ingest.topics.registry import SourceKind, TopicBinding, binding_for
from lib.ingest.types import IngestBundle

_PREFLIGHT_EVAL = "preflight_evaluation_test_topic.json"


def _is_evaluation(topic: str | None) -> bool:
    binding = binding_for(topic) if topic else None
    return bool(binding and binding.evaluation)


def _preflight_path(cfg: dict[str, Any], prefix: str) -> Path:
    return preflight_dir(cfg) / f"preflight_{prefix}.json"


def load_bundle(cfg: dict[str, Any], prefix: str) -> IngestBundle:
    """Build an IngestBundle from on-disk cache only (no network)."""
    pf_path = _preflight_path(cfg, prefix)
    preflight: dict[str, Any] = {}
    if pf_path.is_file():
        preflight = json.loads(pf_path.read_text(encoding="utf-8"))

    crawl_root = cache_dir(cfg) / prefix / "crawl"
    crawl_paths = sorted(crawl_root.glob("*.md")) if crawl_root.is_dir() else []

    structured_root = cache_dir(cfg) / prefix / "structured"
    structured_paths = sorted(structured_root.glob("*.json")) if structured_root.is_dir() else []

    return IngestBundle(
        prefix=prefix,
        preflight_path=pf_path,
        preflight=preflight,
        crawl_paths=[Path(p) for p in crawl_paths],
        structured_paths=[Path(p) for p in structured_paths],
    )


def _copy_fixture(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def ensure_preflight(cfg: dict[str, Any], prefix: str, *, topic: str | None = None) -> Path:
    """Ensure preflight JSON exists for *prefix* (eval fixtures or vendor preflight)."""
    path = _preflight_path(cfg, prefix)
    if path.is_file() and not cfg.get("ingestion", {}).get("force_refetch", False):
        return path

    if _is_evaluation(topic):
        src = evaluation_fixture_path(_PREFLIGHT_EVAL)
        if not src.is_file():
            raise FileNotFoundError(f"evaluation preflight fixture missing: {src}")
        preflight_dir(cfg).mkdir(parents=True, exist_ok=True)
        return _copy_fixture(src, path)

    from lib.ingest.stage1 import run_preflight

    _, saved = run_preflight(cfg, prefix=prefix)
    return saved


def ensure_crawl_slug(
    cfg: dict[str, Any],
    prefix: str,
    slug: str,
    *,
    topic: str | None = None,
) -> Path | None:
    """Ensure one crawl markdown file exists under .cache/<prefix>/crawl/."""
    crawl_root = cache_dir(cfg) / prefix / "crawl"
    crawl_root.mkdir(parents=True, exist_ok=True)
    dest = crawl_root / slug
    if dest.is_file() and not cfg.get("ingestion", {}).get("force_refetch", False):
        return dest

    evaluation = _is_evaluation(topic)
    src = resolve_fixture(slug, evaluation=evaluation)
    if src.is_file():
        return _copy_fixture(src, dest)

    from lib.ingest.stage1 import crawl_one_url

    url = _crawl_url_for_slug(cfg, prefix, slug)
    if url:
        return crawl_one_url(cfg, prefix, url, slug=slug)
    return None


def ensure_structured_slug(
    cfg: dict[str, Any],
    prefix: str,
    slug: str,
    *,
    topic: str | None = None,
) -> Path | None:
    """Ensure one structured JSON file exists under .cache/<prefix>/structured/."""
    structured_root = cache_dir(cfg) / prefix / "structured"
    structured_root.mkdir(parents=True, exist_ok=True)
    dest = structured_root / slug
    if dest.is_file() and not cfg.get("ingestion", {}).get("force_refetch", False):
        return dest

    evaluation = _is_evaluation(topic)
    src = resolve_fixture(slug, evaluation=evaluation)
    if src.is_file():
        return _copy_fixture(src, dest)

    from lib.ingest.stage1 import fetch_one_structured

    return fetch_one_structured(cfg, prefix, slug)


def _crawl_url_for_slug(cfg: dict[str, Any], prefix: str, slug: str) -> str | None:
    if slug == AA_CRAWL_SLUG:
        return "https://artificialanalysis.ai/leaderboards/models"

    pf_path = _preflight_path(cfg, prefix)
    if not pf_path.is_file():
        return None
    data = json.loads(pf_path.read_text(encoding="utf-8"))
    for row in data.get("requires_web_fetch") or []:
        url = str(row.get("url") or "")
        if not url:
            continue
        candidate = url.split("//")[-1].replace("/", "_")[:80]
        if candidate == slug or slug in url:
            return url
    return None


def materialize_binding_cache(
    cfg: dict[str, Any],
    prefix: str,
    binding: TopicBinding,
) -> IngestBundle:
    """Lazy-fetch only the resources listed in *binding*."""
    if SourceKind.PREFLIGHT_CATEGORY in binding.kinds:
        ensure_preflight(cfg, prefix, topic=binding.topic_id)
    for slug in binding.crawl_slugs:
        ensure_crawl_slug(cfg, prefix, slug, topic=binding.topic_id)
    for slug in binding.structured_slugs:
        ensure_structured_slug(cfg, prefix, slug, topic=binding.topic_id)
    return load_bundle(cfg, prefix)
