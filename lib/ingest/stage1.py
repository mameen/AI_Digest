"""Stage-1 ingestion — preflight, Crawl4AI leaderboards, structured APIs.

Shared by ``llm_pipeline/run.py`` and ``lib.ingest.bundle`` (Hermes researchers).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

from llm_pipeline.dates import parse_start, prefix_for_start
from llm_pipeline.diagnostics import get_collector
from llm_pipeline.paths import SKILL_SCRIPTS, cache_dir, preflight_dir


def run_preflight(cfg: dict[str, Any], prefix: str | None = None) -> tuple[str, Path]:
    """
    Run vendored ``preflight.py`` (YouTube chapters, typography, research, llm-stats).

    Returns ``(prefix, path)`` to the saved preflight JSON under ``.preflight/``.
    """
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))

    from preflight import run_preflight as _run, save  # type: ignore

    pfx = prefix or prefix_for_start(parse_start(None))
    force = cfg.get("ingestion", {}).get("force_refetch", False)
    data = _run(pfx, force=force)

    out_dir = preflight_dir(cfg)
    saved = save(data, out_dir / f"preflight_{pfx}.json")
    return pfx, Path(saved)


def crawl_leaderboards(cfg: dict[str, Any], prefix: str, preflight_path: Path) -> list[Path]:
    """Optional Crawl4AI pass over ``requires_web_fetch`` URLs from preflight."""
    crawl_cfg = cfg.get("ingestion", {}).get("crawl4ai", {})
    if not crawl_cfg.get("enabled"):
        return []

    try:
        import asyncio
        from crawl4ai import AsyncWebCrawler  # type: ignore
    except ImportError:
        print("  WARN crawl4ai not installed; skipping leaderboard crawls.")
        print("        pip install crawl4ai && playwright install chromium")
        return []

    data = json.loads(preflight_path.read_text(encoding="utf-8"))
    urls = data.get("requires_web_fetch") or []
    targets = [u["url"] for u in urls if u.get("url")] if crawl_cfg.get("urls_from_preflight") else []

    max_pages = int(crawl_cfg.get("max_pages", 8))
    targets = targets[:max_pages]
    crawl_root = cache_dir(cfg) / prefix / "crawl"
    crawl_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    async def _run() -> None:
        async with AsyncWebCrawler() as crawler:
            for url in targets:
                t0 = time.perf_counter()
                ok = True
                err: str | None = None
                out_name: str | None = None
                nbytes = 0
                try:
                    result = await crawler.arun(url=url)
                    slug = url.split("//")[-1].replace("/", "_")[:80]
                    out = crawl_root / f"{slug}.md"
                    md = getattr(result, "markdown", None) or getattr(result, "markdown_v2", "") or ""
                    out.write_text(str(md), encoding="utf-8")
                    written.append(out)
                    out_name = out.name
                    nbytes = out.stat().st_size
                    print(f"  OK crawl4ai {url} -> {out.name}")
                except Exception as exc:
                    ok = False
                    err = str(exc)
                    nbytes = 0
                    print(f"  WARN crawl4ai {url}: {exc}")
                finally:
                    get_collector().record_crawl(
                        url,
                        (time.perf_counter() - t0) * 1000,
                        ok=ok,
                        output_file=out_name,
                        error=err,
                        bytes_downloaded=nbytes,
                    )

    try:
        asyncio.run(_run())
    except Exception as exc:
        print(f"  WARN crawl4ai failed; continuing without crawls: {exc}")
        return written
    return written


def fetch_structured_sources(cfg: dict[str, Any], prefix: str) -> list[Path]:
    """Download structured-API leaderboard JSON (no scraping) into the run cache."""
    import urllib.request

    from llm_pipeline.structured_sources import STRUCTURED_SOURCES

    if not cfg.get("ingestion", {}).get("structured_sources", {}).get("enabled", True):
        return []

    out_dir = cache_dir(cfg) / prefix / "structured"
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "AI-Digest/1.0", "Accept": "application/json,*/*"}
    written: list[Path] = []
    for src in STRUCTURED_SOURCES:
        t0 = time.perf_counter()
        ok, err, out_name, nbytes = True, None, None, 0
        try:
            req = urllib.request.Request(src["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read().decode("utf-8", "replace")
            json.loads(raw)  # validate before persisting
            out = out_dir / src["slug"]
            out.write_text(raw, encoding="utf-8")
            written.append(out)
            out_name = out.name
            nbytes = out.stat().st_size
            print(f"  OK structured {src['label']} -> {out.name}")
        except Exception as exc:
            ok, err = False, str(exc)
            print(f"  WARN structured {src['label']}: {exc}")
        finally:
            get_collector().record_crawl(
                src["url"],
                (time.perf_counter() - t0) * 1000,
                ok=ok,
                output_file=out_name,
                error=err,
                bytes_downloaded=nbytes,
            )
    return written


def crawl_one_url(
    cfg: dict[str, Any],
    prefix: str,
    url: str,
    *,
    slug: str | None = None,
) -> Path | None:
    """Crawl a single URL into ``.cache/<prefix>/crawl/<slug>.md``."""
    crawl_cfg = cfg.get("ingestion", {}).get("crawl4ai", {})
    if not crawl_cfg.get("enabled", True):
        return None

    try:
        import asyncio
        from crawl4ai import AsyncWebCrawler  # type: ignore
    except ImportError:
        print(f"  WARN crawl4ai not installed; skipping {url}")
        return None

    crawl_root = cache_dir(cfg) / prefix / "crawl"
    crawl_root.mkdir(parents=True, exist_ok=True)
    out_name = slug or url.split("//")[-1].replace("/", "_")[:80]
    out = crawl_root / out_name

    async def _run() -> None:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            md = getattr(result, "markdown", None) or getattr(result, "markdown_v2", "") or ""
            out.write_text(str(md), encoding="utf-8")
            print(f"  OK crawl4ai {url} -> {out.name}")

    try:
        asyncio.run(_run())
    except Exception as exc:
        print(f"  WARN crawl4ai {url}: {exc}")
        return None
    return out if out.is_file() else None


def fetch_one_structured(cfg: dict[str, Any], prefix: str, slug: str) -> Path | None:
    """Download one structured-API JSON payload by slug."""
    import urllib.request

    from llm_pipeline.structured_sources import STRUCTURED_SOURCES

    if not cfg.get("ingestion", {}).get("structured_sources", {}).get("enabled", True):
        return None

    src = next((s for s in STRUCTURED_SOURCES if s["slug"] == slug), None)
    if src is None:
        return None

    out_dir = cache_dir(cfg) / prefix / "structured"
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "AI-Digest/1.0", "Accept": "application/json,*/*"}
    out = out_dir / slug
    t0 = time.perf_counter()
    ok, err, out_name, nbytes = True, None, None, 0
    try:
        req = urllib.request.Request(src["url"], headers=headers)
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", "replace")
        json.loads(raw)
        out.write_text(raw, encoding="utf-8")
        out_name = out.name
        nbytes = out.stat().st_size
        print(f"  OK structured {src['label']} -> {out.name}")
    except Exception as exc:
        ok, err = False, str(exc)
        print(f"  WARN structured {src['label']}: {exc}")
        return None
    finally:
        get_collector().record_crawl(
            src["url"],
            (time.perf_counter() - t0) * 1000,
            ok=ok,
            output_file=out_name,
            error=err,
            bytes_downloaded=nbytes,
        )
    return out if out.is_file() else None
