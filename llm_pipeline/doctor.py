"""Pre-run self-check ("doctor"): verify the environment before a 10-minute run.

Front-loads the failures that otherwise surface mid-run: Ollama/model missing,
enrich deps absent, unwritable output dirs, unreachable sources. It self-heals
where safe (ensures dirs exist, retries throttled source probes with backoff)
and emits a clear go/no-go so the pipeline can be run without an LLM babysitter.

Blocking (FAIL) checks stop the run unless ``--force``; soft issues (a throttled
source that has a fallback / graceful degradation) are WARN and never block.

The only I/O seams (``tags_fetch`` for Ollama, ``probe`` for source reachability,
``sleep`` for backoff) are dependency-injected so the real logic is testable
against fixtures without network access.
"""

from __future__ import annotations

import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

from llm_pipeline.paths import SKILL_SCRIPTS, cache_dir, diagnostics_dir, preflight_dir, reports_dir

OK, WARN, FAIL = "OK", "WARN", "FAIL"
# ASCII-only markers: render_text prints to the console, which on Windows is
# often cp1252 and cannot encode check/warn glyphs (would crash the run).
_SYMBOL = {OK: "+", WARN: "!", FAIL: "x"}


@dataclass
class Check:
    name: str
    level: str
    detail: str = ""
    hint: str = ""


@dataclass
class DoctorReport:
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(c.level == FAIL for c in self.checks)

    @property
    def status(self) -> str:
        if any(c.level == FAIL for c in self.checks):
            return "fail"
        return "degraded" if any(c.level == WARN for c in self.checks) else "ok"

    def render_text(self) -> str:
        lines = [f"Pre-run self-check: {self.status.upper()}"]
        for c in self.checks:
            lines.append(f"  {_SYMBOL.get(c.level, '?')} [{c.level}] {c.name}: {c.detail}")
            if c.hint and c.level != OK:
                lines.append(f"      -> {c.hint}")
        return "\n".join(lines)


# ── Default I/O seams ────────────────────────────────────────────────────────

def _default_tags_fetch(url: str, timeout: int = 5) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _default_probe(url: str, timeout: int = 8) -> bool:
    """Reachable = we got *any* HTTP response (even 4xx/5xx = throttled but up)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


# ── Individual checks ────────────────────────────────────────────────────────

def _check_deps(skeleton_only: bool, llm_enabled: bool) -> Check:
    if skeleton_only or not llm_enabled:
        return Check("enrich deps", OK, "skipped (skeleton-only / llm disabled)")
    missing = [m for m in ("instructor", "openai") if not _importable(m)]
    if missing:
        return Check("enrich deps", FAIL, f"missing: {', '.join(missing)}",
                     "pip install -r requirements.txt")
    return Check("enrich deps", OK, "instructor + openai importable")


def _importable(mod: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(mod) is not None


def _check_ollama(cfg: dict[str, Any], tags_fetch: Callable[[str], str]) -> list[Check]:
    llm = cfg.get("llm") or {}
    base = str(llm.get("base_url", "http://localhost:11434/v1")).rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    model = llm.get("model", "llama3.1:latest")
    try:
        payload = tags_fetch(f"{base}/api/tags")
    except Exception as exc:
        return [Check("Ollama", FAIL, f"unreachable at {base} ({exc})",
                      f"Start Ollama, then: ollama pull {model}  (or run --skeleton-only)")]
    reach = Check("Ollama", OK, f"reachable at {base}")
    if model in payload or f'"{model}"' in payload:
        return [reach, Check("Ollama model", OK, f"{model} present")]
    return [reach, Check("Ollama model", FAIL, f"{model} not installed",
                         f"ollama pull {model}")]


def _check_paths(cfg: dict[str, Any]) -> Check:
    unwritable: list[str] = []
    for name, fn in (("reports", reports_dir), ("cache", cache_dir),
                     ("preflight", preflight_dir), ("diagnostics", diagnostics_dir)):
        try:
            d = fn(cfg)  # _resolve_dir already mkdirs (self-heal)
            probe = d / ".doctor_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except Exception as exc:
            unwritable.append(f"{name} ({exc})")
    if unwritable:
        return Check("output paths", FAIL, "unwritable: " + "; ".join(unwritable),
                     "check permissions / disk space for the output dirs")
    return Check("output paths", OK, "reports/cache/preflight/diagnostics writable")


def _source_urls(cfg: dict[str, Any]) -> dict[str, str]:
    urls: dict[str, str] = {}
    if str(SKILL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SKILL_SCRIPTS))
    try:
        from fetch_robotics_news import SOURCES as ROBO  # type: ignore
        urls.update({f"robotics:{s}": u for s, (u, _l) in ROBO.items()})
    except Exception:
        pass
    try:
        from preflight import REQUIRES_WEB_FETCH  # type: ignore
        urls.update({f"leaderboard:{i['label']}": i["url"] for i in REQUIRES_WEB_FETCH if i.get("url")})
    except Exception:
        pass
    if (cfg.get("ingestion") or {}).get("structured_sources", {}).get("enabled", True):
        try:
            from llm_pipeline.structured_sources import STRUCTURED_SOURCES
            urls.update({f"structured:{s.get('key', s.get('url'))}": s["url"]
                         for s in STRUCTURED_SOURCES if s.get("url")})
        except Exception:
            pass
    return urls


def _probe_with_retry(
    url: str, probe: Callable[[str], bool], sleep: Callable[[float], None],
    attempts: int = 2, backoff: float = 1.5,
) -> bool:
    """Self-heal transient throttling: retry a failed probe with backoff."""
    for attempt in range(attempts):
        if probe(url):
            return True
        if attempt < attempts - 1:
            sleep(backoff * (attempt + 1))
    return False


def _check_sources(
    cfg: dict[str, Any],
    probe: Callable[[str], bool],
    sleep: Callable[[float], None],
) -> Check:
    """Probe known sources in parallel. Sources degrade gracefully, so an
    unreachable source is WARN (never blocks): the pipeline has fallbacks
    (yt-dlp for RSS, carry-forward for categories, seed rows for leaderboards).
    """
    urls = _source_urls(cfg)
    if not urls:
        return Check("sources", WARN, "no source list available to probe",
                     "check that fetch_robotics_news / preflight import cleanly")
    unreachable: list[str] = []
    with ThreadPoolExecutor(max_workers=min(8, len(urls))) as pool:
        futures = {
            pool.submit(_probe_with_retry, url, probe, sleep): name
            for name, url in urls.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                if not future.result():
                    unreachable.append(name)
            except Exception:
                unreachable.append(name)
    total = len(urls)
    reachable = total - len(unreachable)
    if unreachable:
        return Check("sources", WARN,
                     f"{reachable}/{total} reachable; down: {', '.join(sorted(unreachable))}",
                     "these degrade gracefully (fallbacks/seed rows); rerun later if unexpected")
    return Check("sources", OK, f"{reachable}/{total} reachable")


def run_doctor(
    cfg: dict[str, Any],
    *,
    skeleton_only: bool = False,
    tags_fetch: Callable[[str], str] = _default_tags_fetch,
    probe: Callable[[str], bool] = _default_probe,
    sleep: Callable[[float], None] = time.sleep,
    check_sources: bool = True,
) -> DoctorReport:
    """Run all pre-flight checks and return a structured go/no-go report."""
    report = DoctorReport()
    llm_enabled = bool((cfg.get("llm") or {}).get("enabled"))

    report.checks.append(_check_deps(skeleton_only, llm_enabled))
    if llm_enabled and not skeleton_only:
        report.checks.extend(_check_ollama(cfg, tags_fetch))
    else:
        report.checks.append(Check("Ollama", OK, "skipped (skeleton-only / llm disabled)"))
    report.checks.append(_check_paths(cfg))
    if check_sources:
        report.checks.append(_check_sources(cfg, probe, sleep))
    return report
