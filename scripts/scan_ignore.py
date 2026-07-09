"""Gitignore-style path exemptions for PII/secret audit scanners.

Reads ``.piiignore`` and ``.ignorepii`` (alias) from the repo root.
Syntax matches ``.gitignore`` (``#`` comments, ``/`` prefix, ``**``, ``*``).

Important: exemptions apply to **audit scans** (Presidio, Betterleaks tree walks).
``check_secrets.py`` still **blocks** gitignored vault paths if they are staged.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path

IGNORE_FILENAMES = (".piiignore", ".ignorepii")


def load_patterns(repo: Path) -> tuple[str, ...]:
    patterns: list[str] = []
    for name in IGNORE_FILENAMES:
        path = repo / name
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.append(line)
    return tuple(patterns)


def _match_pattern(rel: str, pattern: str) -> bool:
    rel = rel.replace("\\", "/").lstrip("./")
    pat = pattern.replace("\\", "/").lstrip("./")

    if pat.endswith("/"):
        prefix = pat.rstrip("/")
        return rel == prefix or rel.startswith(prefix + "/")

    if "/" in pat:
        return fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat.lstrip("/"))

    # No slash — match any path segment
    if fnmatch.fnmatch(rel, pat):
        return True
    parts = rel.split("/")
    return any(fnmatch.fnmatch(part, pat) for part in parts)


def is_ignored(rel: str, patterns: tuple[str, ...] | None = None, *, repo: Path | None = None) -> bool:
    if patterns is None:
        if repo is None:
            raise ValueError("repo required when patterns is None")
        patterns = load_patterns(repo)
    rel = rel.replace("\\", "/").lstrip("./")
    return any(_match_pattern(rel, p) for p in patterns)
