#!/usr/bin/env python3
"""Secret scan: Betterleaks / Gitleaks (preferred) or detect-secrets (pip fallback).

Respects ``.gitleaksignore`` (standard) and ``.piiignore`` / ``.ignorepii``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from scan_ignore import is_ignored, load_patterns  # noqa: E402

BASELINE = REPO / ".secrets.baseline"

# Scanner sources contain intentional secret-shaped test patterns.
_SKIP_SECRET_SCAN = frozenset(
    {
        "scripts/check_secrets.py",
        "scripts/audit_secrets.py",
        "scripts/audit_pii.py",
        "scripts/scan_ignore.py",
        ".secrets.baseline",
    }
)


def _fail(msg: str) -> None:
    print(f"✗ secrets audit: {msg}", file=sys.stderr)
    sys.exit(1)


def _staged_paths() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return []
    return [line.strip() for line in out.stdout.splitlines() if line.strip()]


def _filter_ignored(paths: list[str]) -> list[str]:
    patterns = load_patterns(REPO)
    return [
        p
        for p in paths
        if p not in _SKIP_SECRET_SCAN and not is_ignored(p, patterns)
    ]


def _run_cli_protect(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    if proc.stdout:
        print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
    if proc.stderr:
        print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n", file=sys.stderr)
    return proc.returncode


def _scan_with_gitleaks_family(binary: str, staged_only: bool) -> int:
    gignore = REPO / ".gitleaksignore"
    cmd = [binary, "protect", "--verbose", "--redact"]
    if gignore.is_file():
        cmd.extend(["--gitleaks-ignore-path", str(gignore)])
    config = REPO / ".gitleaks.toml"
    if config.is_file():
        cmd.extend(["--config", str(config)])
    if staged_only:
        cmd.append("--staged")
    else:
        cmd.extend(["--source", str(REPO)])
    return _run_cli_protect(cmd)


def _ensure_detect_secrets() -> None:
    try:
        import detect_secrets  # noqa: F401
    except ImportError:
        _fail(
            "install a secret scanner:\n"
            "  brew install betterleaks   # or gitleaks\n"
            "  pip install -r requirements-dev.txt"
        )


def _ensure_baseline() -> None:
    if BASELINE.is_file():
        return
    proc = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan", "--all-files"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        _fail(proc.stderr or proc.stdout or "detect-secrets scan failed")
    BASELINE.write_text(proc.stdout, encoding="utf-8")


def _scan_with_detect_secrets(staged_only: bool) -> int:
    _ensure_detect_secrets()
    _ensure_baseline()

    if staged_only:
        paths = _filter_ignored(_staged_paths())
        if not paths:
            return 0
        hook = shutil.which("detect-secrets-hook")
        if hook:
            return subprocess.run([hook, "--baseline", str(BASELINE), *paths], cwd=REPO).returncode
        proc = subprocess.run(
            [sys.executable, "-m", "detect_secrets", "scan", "--baseline", str(BASELINE), *paths],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(proc.stdout or proc.stderr, file=sys.stderr)
        return proc.returncode

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "detect_secrets",
            "scan",
            "--baseline",
            str(BASELINE),
            "--all-files",
            "--exclude-files",
            r"scripts/(check_secrets|audit_secrets|audit_pii|scan_ignore)\.py|\.secrets\.baseline",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(proc.stdout or proc.stderr, file=sys.stderr)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Secret audit (Betterleaks / detect-secrets).")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args(argv)
    staged_only = args.staged or not args.all

    for binary in ("betterleaks", "gitleaks"):
        if shutil.which(binary):
            rc = _scan_with_gitleaks_family(binary, staged_only=staged_only)
            if rc != 0:
                print("ERROR: secret scan failed.", file=sys.stderr)
            return rc

    return _scan_with_detect_secrets(staged_only=staged_only)


if __name__ == "__main__":
    raise SystemExit(main())
