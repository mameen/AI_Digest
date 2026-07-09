"""Capture run-time hardware and network context for diagnostics.

Designed so CUDA workstation and Mac (Metal) profiles can coexist in the
archive without schema churn — ``platform_kind`` discriminates profiles.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any

SCHEMA = "ai_digest.environment/v1"

# Heuristic profile for diagnostics JSON written before environment capture existed.
# Marked ``inferred`` — GPU only; CPU/RAM left empty when unknown.
LEGACY_RTX4090_ENV: dict[str, Any] = {
    "schema": SCHEMA,
    "platform_kind": "cuda",
    "inferred": True,
    "os": None,
    "os_release": None,
    "machine": None,
    "cpu": None,
    "cpu_count": None,
    "ram_gb": None,
    "gpu": {
        "name": "NVIDIA GeForce RTX 4090",
        "backend": "cuda",
        "vram_gb": 24.0,
    },
    "python": None,
    "hostname": None,
}


def _env_populated(env: dict[str, Any] | None) -> bool:
    return bool(env and env.get("platform_kind"))


def backfill_environment(env: dict[str, Any] | None) -> dict[str, Any]:
    """Fill missing environment from legacy workstation assumption (RTX 4090)."""
    if _env_populated(env):
        return dict(env)
    return dict(LEGACY_RTX4090_ENV)


def backfill_network(
    report: dict[str, Any],
    *,
    cache_root: Path | None = None,
    preflight_path: Path | None = None,
) -> dict[str, Any]:
    """Derive network summary from crawls / cache when older JSON lacks ``network``."""
    existing = report.get("network") or {}
    if existing.get("bytes_downloaded") or existing.get("throughput_mbps") is not None:
        return dict(existing)

    crawls = report.get("crawls") or []
    ingest_ms = sum(
        float(st.get("duration_ms") or 0)
        for st in report.get("stages") or []
        if st.get("id") in ("ingestion.preflight", "ingestion.crawl4ai", "ingestion.structured")
    )
    summary = summarize_network(
        crawls,
        cache_root=cache_root,
        preflight_path=preflight_path,
        ingest_duration_ms=ingest_ms or None,
    )
    if summary.get("bytes_downloaded") or summary.get("throughput_mbps"):
        summary["inferred"] = not crawls or not any(c.get("bytes_downloaded") for c in crawls)
        return summary
    return dict(existing)


def enrich_diagnostics_report(
    report: dict[str, Any],
    *,
    cache_root: Path | None = None,
    preflight_path: Path | None = None,
) -> dict[str, Any]:
    """Ensure ``environment`` and ``network`` keys exist (non-destructive)."""
    out = dict(report)
    out["environment"] = backfill_environment(report.get("environment"))
    net = backfill_network(
        report,
        cache_root=cache_root,
        preflight_path=preflight_path,
    )
    if net:
        out["network"] = net
    return out


def hw_metric_cards(env: dict[str, Any] | None, net: dict[str, Any] | None) -> list[tuple[str, str]]:
    """Label/value pairs for diagnostics HTML hardware cards."""
    env = env or {}
    net = net or {}
    gpu = env.get("gpu") or {}
    inferred = " (est.)" if env.get("inferred") else ""

    def _fmt_gb(value: float | int | None) -> str:
        if value is None:
            return "—"
        return f"{value} GB"

    cpu = env.get("cpu") or "—"
    if env.get("cpu_count"):
        cpu = f"{cpu} ×{env['cpu_count']}" if cpu != "—" else f"×{env['cpu_count']}"

    return [
        ("CPU", cpu),
        ("GPU", (gpu.get("name") or "—") + inferred),
        ("RAM", _fmt_gb(env.get("ram_gb"))),
        ("VRAM", _fmt_gb(gpu.get("vram_gb"))),
        (
            "Net BW",
            f"{net['throughput_mbps']} Mbps" if net.get("throughput_mbps") is not None else "—",
        ),
    ]


def format_env_line(env: dict[str, Any] | None) -> str:
    env = env or {}
    gpu = env.get("gpu") or {}
    suffix = " (estimated)" if env.get("inferred") else ""
    return " · ".join(
        part
        for part in [
            env.get("platform_kind"),
            env.get("cpu"),
            f"{env.get('ram_gb')} GB RAM" if env.get("ram_gb") else None,
            (gpu.get("name") or "") + suffix if gpu.get("name") else None,
            f"{gpu.get('vram_gb')} GB VRAM" if gpu.get("vram_gb") else None,
        ]
        if part
    )


def format_net_line(net: dict[str, Any] | None) -> str:
    net = net or {}
    if not net.get("bytes_downloaded") and net.get("throughput_mbps") is None:
        return ""

    def _ms_label(ms: float) -> str:
        if ms >= 60_000:
            return f"{ms / 60_000:.1f}m"
        if ms >= 1000:
            return f"{ms / 1000:.1f}s"
        return f"{ms:.0f}ms"

    parts: list[str] = []
    if net.get("bytes_downloaded"):
        mb = net["bytes_downloaded"] / (1024 * 1024)
        parts.append(f"{mb:.1f} MB downloaded")
    if net.get("throughput_mbps") is not None:
        label = f"{net['throughput_mbps']} Mbps avg"
        if net.get("inferred"):
            label += " (est.)"
        parts.append(label)
    if net.get("duration_ms"):
        parts.append(f"ingest {_ms_label(float(net['duration_ms']))}")
    return " · ".join(parts)


def _run(cmd: list[str], *, timeout: float = 6.0) -> str | None:
    if not cmd or not shutil.which(cmd[0]):
        return None
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None


def _ram_gb() -> float | None:
    system = platform.system()
    if system == "Darwin":
        raw = _run(["sysctl", "-n", "hw.memsize"])
        if raw:
            try:
                return round(int(raw) / (1024**3), 1)
            except ValueError:
                pass
    if system == "Linux":
        try:
            with open("/proc/meminfo", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024**2), 1)
        except OSError:
            pass
    return None


def _cpu_label() -> str:
    system = platform.system()
    if system == "Darwin":
        brand = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if brand:
            return brand
    return platform.processor() or platform.machine() or "unknown"


def _detect_cuda_gpu() -> dict[str, Any] | None:
    raw = _run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total",
            "--format=csv,noheader,nounits",
        ],
        timeout=8.0,
    )
    if not raw:
        return None
    line = raw.splitlines()[0]
    parts = [p.strip() for p in line.split(",")]
    gpu: dict[str, Any] = {"name": parts[0], "backend": "cuda"}
    if len(parts) > 1:
        try:
            # nvidia-smi reports MiB
            gpu["vram_gb"] = round(float(parts[1]) / 1024, 1)
        except ValueError:
            pass
    return gpu


def _detect_mac_gpu() -> dict[str, Any]:
    gpu: dict[str, Any] = {"backend": "metal", "name": _cpu_label()}
    raw = _run(["system_profiler", "SPDisplaysDataType", "-json"], timeout=10.0)
    if raw:
        try:
            data = json.loads(raw)
            for item in data.get("SPDisplaysDataType") or []:
                name = item.get("sppci_model") or item.get("_name")
                if name:
                    gpu["name"] = str(name)
                    break
        except (json.JSONDecodeError, TypeError):
            pass
    return gpu


def detect_platform_kind() -> str:
    """Return ``cuda``, ``mac``, ``cpu``, or ``unknown`` for archive filtering."""
    if _detect_cuda_gpu() is not None:
        return "cuda"
    if platform.system() == "Darwin":
        return "mac"
    if platform.machine().lower() in {"x86_64", "amd64", "aarch64", "arm64"}:
        return "cpu"
    return "unknown"


def capture_environment() -> dict[str, Any]:
    """Snapshot the machine running the pipeline (stdlib + optional nvidia-smi)."""
    cuda = _detect_cuda_gpu()
    if cuda:
        gpu = cuda
        platform_kind = "cuda"
    elif platform.system() == "Darwin":
        gpu = _detect_mac_gpu()
        platform_kind = "mac"
    else:
        gpu = {"backend": "cpu", "name": _cpu_label()}
        platform_kind = "cpu"

    return {
        "schema": SCHEMA,
        "platform_kind": platform_kind,
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "cpu": _cpu_label(),
        "cpu_count": os.cpu_count(),
        "ram_gb": _ram_gb(),
        "gpu": gpu,
        "python": platform.python_version(),
        "hostname": platform.node() or None,
    }


def summarize_network(
    crawls: list[dict[str, Any]],
    *,
    cache_root: Path | None = None,
    preflight_path: Path | None = None,
    ingest_duration_ms: float | None = None,
) -> dict[str, Any]:
    """Aggregate download volume and throughput for the ingest phase."""
    active_ms = sum(float(cr.get("duration_ms") or 0) for cr in crawls)
    bytes_downloaded = 0
    seen: set[Path] = set()
    for path in (cache_root, preflight_path):
        if path is None:
            continue
        files = [path] if path.is_file() else [p for p in path.rglob("*") if p.is_file()] if path.is_dir() else []
        for fp in files:
            rp = fp.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            try:
                bytes_downloaded += fp.stat().st_size
            except OSError:
                pass
    if bytes_downloaded == 0:
        bytes_downloaded = sum(int(cr.get("bytes_downloaded") or 0) for cr in crawls)

    duration_ms = float(ingest_duration_ms if ingest_duration_ms is not None else active_ms)
    throughput_mbps = None
    if duration_ms > 0 and bytes_downloaded > 0:
        throughput_mbps = round((bytes_downloaded * 8) / (duration_ms / 1000) / 1_000_000, 2)

    return {
        "bytes_downloaded": bytes_downloaded,
        "duration_ms": round(duration_ms, 1),
        "throughput_mbps": throughput_mbps,
    }
