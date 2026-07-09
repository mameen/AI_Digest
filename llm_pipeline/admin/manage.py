#!/usr/bin/env python3
"""
Pipeline admin — venv bootstrap, nuke cache/config/runs, doctor, status.

Usage:
    python admin/manage.py bootstrap [--skip-doctor] [--recreate-venv] [--locked]
    python admin/manage.py freeze-requirements
    python admin/manage.py nuke ephemeral [--yes]
    python admin/manage.py nuke config [--yes]
    python admin/manage.py nuke run YYYYMMDDHHMMSS [--yes]
    python admin/manage.py doctor
    python admin/manage.py status

Agentic Hermes (profiles, kanban, dashboard): ``python agentic/hermes/admin/manage.py``.
Digest web UI: ``python run.py --server`` (feat/admin-local-server branch).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from lib.paths import LLM_PIPELINE_ROOT

PIPELINE = LLM_PIPELINE_ROOT
CONFIG_DIR = Path(__file__).resolve().parent / "config"
MANIFEST_PATH = CONFIG_DIR / "manifest.yaml"
TEMPLATES = CONFIG_DIR / "templates"
VENV_DIR = REPO / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"


def _uv_bin() -> str | None:
    return shutil.which("uv")


def _venv_python_ok() -> bool:
    if not VENV_PYTHON.is_file():
        return False
    proc = subprocess.run(
        [str(VENV_PYTHON), "-c", "import sys"],
        cwd=REPO,
        capture_output=True,
    )
    return proc.returncode == 0


def _ensure_venv(*, force: bool = False) -> None:
    if force and VENV_DIR.is_dir():
        print("Removing .venv …")
        shutil.rmtree(VENV_DIR)
    elif VENV_DIR.is_dir() and not _venv_python_ok():
        print("Removing broken .venv (stale path or corrupt) …")
        shutil.rmtree(VENV_DIR)

    if _venv_python_ok():
        return

    uv = _uv_bin()
    print(f"Creating .venv … ({'uv' if uv else 'stdlib venv'})")
    if uv:
        subprocess.run([uv, "venv", str(VENV_DIR)], cwd=REPO, check=True)
    else:
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)


def _install_requirements(*, locked: bool = False) -> None:
    req_name = "requirements-lock.txt" if locked else "requirements.txt"
    req_path = REPO / req_name
    if locked and not req_path.is_file():
        print(f"Missing {req_name} — run: python admin/manage.py freeze-requirements")
        sys.exit(1)
    uv = _uv_bin()
    if uv:
        print(f"Installing deps (uv pip, {req_name}) …")
        subprocess.run(
            [uv, "pip", "install", "-r", str(req_path)],
            cwd=REPO,
            check=True,
        )
    else:
        print(f"Installing deps (pip, {req_name}) …  tip: install uv for faster bootstrap")
        subprocess.run(
            [str(VENV_PYTHON), "-m", "pip", "install", "-q", "-r", str(req_path)],
            cwd=REPO,
            check=True,
        )


def _venv_py(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(VENV_PYTHON), *args], cwd=REPO, check=check)


def _load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _confirm(yes: bool, tier: str) -> None:
    if yes:
        return
    print(f"Dry run ({tier}) — re-run with --yes to execute.")
    sys.exit(1)


def _rm(path: Path) -> None:
    if not path.exists():
        return
    print(f"  rm {path.relative_to(REPO)}")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def cmd_status(_: argparse.Namespace) -> int:
    print(f"Repo: {REPO}")
    rows = [
        ("llm_pipeline/.cache", (PIPELINE / ".cache").exists()),
        ("llm_pipeline/.preflight", (PIPELINE / ".preflight").exists()),
        (".venv", (REPO / ".venv").is_dir()),
        ("llm_pipeline/config.yaml", (PIPELINE / "config.yaml").is_file()),
    ]
    for name, ok in rows:
        print(f"  {'✓' if ok else '·'} {name}")
    uv = _uv_bin()
    print(f"  {'✓' if uv else '·'} uv ({uv or 'not on PATH — bootstrap uses pip'})")
    print("  Agentic Hermes: python agentic/hermes/admin/manage.py status")
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    print("== bootstrap ==")
    _ensure_venv(force=getattr(args, "recreate_venv", False))
    _install_requirements(locked=getattr(args, "locked", False))
    pw = _venv_py("-m", "playwright", "install", "chromium", check=False)
    if pw.returncode != 0:
        print("  WARN: playwright install failed — crawl may fail until fixed")

    env_example = REPO / ".env.example"
    env_file = REPO / ".env"
    if env_example.is_file() and not env_file.is_file():
        shutil.copy(env_example, env_file)
        print("Created .env from .env.example")

    brief = REPO / "llm_pipeline" / "editorial_brief.md"
    shim = REPO / "pipeline" / "editorial_brief.md"
    if brief.is_file() and not shim.exists():
        shim.parent.mkdir(exist_ok=True)
        try:
            shim.symlink_to("../llm_pipeline/editorial_brief.md")
        except OSError:
            pass

    if args.skip_doctor:
        print("Skipping doctor.")
    else:
        _venv_py("run.py", "--doctor", check=False)

    tool = "uv" if _uv_bin() else "pip"
    print(f"\nDone ({tool}).")
    print("  Pipeline digest:  python run.py --start YYYY-MM-DD")
    print("  Agentic Hermes:   python agentic/hermes/admin/manage.py bootstrap")
    print("  nuke:             python admin/manage.py nuke ephemeral --yes")
    return 0


def _nuke_ephemeral(manifest: dict[str, Any], yes: bool) -> None:
    print("== nuke ephemeral ==")
    print("Removes cache, preflight, pycache. Keeps reports/ + config.")
    _confirm(yes, "ephemeral")
    for rel in manifest.get("ephemeral", {}).get("dirs", []):
        _rm(PIPELINE / rel)
    for p in REPO.rglob("__pycache__"):
        if p.is_dir():
            _rm(p)
    for p in REPO.rglob("*.pyc"):
        if p.is_file():
            _rm(p)
    for p in REPO.rglob("*.log"):
        if p.is_file() and ".git" not in p.parts:
            _rm(p)
    print("Ephemeral state cleared.")


def _nuke_config(manifest: dict[str, Any], yes: bool) -> None:
    _nuke_ephemeral(manifest, yes=True)
    print("\n== nuke config ==")
    print("Restores config.yaml + editorial_brief from admin/config/templates/")
    _confirm(yes, "config")
    for entry in manifest.get("config_restore", {}).get("files", []):
        src = CONFIG_DIR / entry["source"]
        dest = PIPELINE / entry["dest"]
        if not src.is_file():
            print(f"  ERROR missing template: {src}")
            sys.exit(1)
        print(f"  cp {src.relative_to(REPO)} → {dest.relative_to(REPO)}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)
    print("Config restored.")


def _nuke_run(prefix: str, yes: bool) -> None:
    if not prefix.isdigit() or len(prefix) != 14:
        print("Prefix must be YYYYMMDDHHMMSS (14 digits)")
        sys.exit(1)
    print(f"== nuke run {prefix} ==")
    _confirm(yes, f"run {prefix}")
    for d in ("reports", "diagnostics"):
        for ext in (".json", ".html", ".diagnostics.json", ".diagnostics.html"):
            _rm(PIPELINE / d / f"{prefix}{ext}")
    _rm(PIPELINE / ".cache" / prefix)
    _rm(PIPELINE / ".preflight" / f"preflight_{prefix}.json")
    print("Run removed. Rebuild archives from run.py --server if needed.")


def cmd_nuke(args: argparse.Namespace) -> int:
    manifest = _load_manifest()
    tier = args.tier
    yes = args.yes
    if tier == "ephemeral":
        _nuke_ephemeral(manifest, yes)
    elif tier == "config":
        _nuke_config(manifest, yes)
    elif tier == "run":
        if not args.prefix:
            print("Usage: python admin/manage.py nuke run YYYYMMDDHHMMSS [--yes]")
            return 1
        _nuke_run(args.prefix, yes)
    else:
        print(f"Unknown tier: {tier!r}. Use: ephemeral | config | run")
        return 1
    return 0


def cmd_doctor(_: argparse.Namespace) -> int:
    if not _venv_python_ok():
        print("No .venv — run: python admin/manage.py bootstrap")
        return 1
    return _venv_py("run.py", "--doctor", check=False).returncode


def cmd_freeze_requirements(_: argparse.Namespace) -> int:
    if not _venv_python_ok():
        print("No .venv — run: python admin/manage.py bootstrap")
        return 1
    lock_path = REPO / "requirements-lock.txt"
    proc = subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "freeze"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    header = (
        "# Auto-generated full pin set — regenerate with:\n"
        "#   python admin/manage.py freeze-requirements\n"
        "# Install: python admin/manage.py bootstrap --locked\n\n"
    )
    lock_path.write_text(header + proc.stdout.strip() + "\n", encoding="utf-8")
    print(f"Wrote {lock_path.relative_to(REPO)} ({len(proc.stdout.splitlines())} packages)")
    print("Commit requirements.txt (minimums) + requirements-lock.txt after dependency changes.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Digest pipeline admin")
    sub = parser.add_subparsers(dest="command", required=True)

    p_boot = sub.add_parser("bootstrap", help="venv (uv if available), deps, playwright, doctor")
    p_boot.add_argument("--skip-doctor", action="store_true")
    p_boot.add_argument(
        "--locked",
        action="store_true",
        help="install from requirements-lock.txt (exact pins) instead of requirements.txt",
    )
    p_boot.add_argument(
        "--recreate-venv",
        action="store_true",
        help="delete .venv and create fresh (fixes stale/moved venv paths)",
    )
    p_boot.set_defaults(func=cmd_bootstrap)

    p_nuke = sub.add_parser("nuke", help="tiered reset (see manifest.yaml)")
    p_nuke.add_argument("tier", choices=("ephemeral", "config", "run"))
    p_nuke.add_argument("prefix", nargs="?", help="run prefix when tier=run")
    p_nuke.add_argument("--yes", action="store_true", help="execute (default is dry run)")
    p_nuke.set_defaults(func=cmd_nuke)

    p_doc = sub.add_parser("doctor", help="run pipeline doctor")
    p_doc.set_defaults(func=cmd_doctor)

    p_freeze = sub.add_parser(
        "freeze-requirements",
        help="write requirements-lock.txt from the current .venv (after green tests)",
    )
    p_freeze.set_defaults(func=cmd_freeze_requirements)

    p_st = sub.add_parser("status", help="show pipeline state paths")
    p_st.set_defaults(func=cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
