"""Persist agentic board artifacts outside Hermes scratch workspaces."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from tools.artifacts import DIGEST_ARTIFACT, LIBRARIAN_ARTIFACT, RESEARCH_ARTIFACT

# Survives Hermes workspace wipe on kanban_complete.
RUNTIME_ROOT = Path(__file__).resolve().parents[1] / ".runtime" / "artifacts"


def run_dir(prefix: str) -> Path:
    return RUNTIME_ROOT / prefix


def _research_dir(prefix: str) -> Path:
    return run_dir(prefix) / "research"


def persist_research(prefix: str, topic: str, workspace: Path) -> Path | None:
    src = workspace / RESEARCH_ARTIFACT
    if not src.is_file():
        return None
    dest_dir = _research_dir(prefix)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{topic}.md"
    shutil.copy2(src, dest)
    return dest


def load_research_text(prefix: str, topic: str) -> str | None:
    path = _research_dir(prefix) / f"{topic}.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def persist_librarian(prefix: str, workspace: Path) -> Path | None:
    src = workspace / LIBRARIAN_ARTIFACT
    if not src.is_file():
        return None
    dest_dir = run_dir(prefix)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / LIBRARIAN_ARTIFACT
    shutil.copy2(src, dest)
    return dest


def persist_digest(prefix: str, workspace: Path) -> Path | None:
    src = workspace / DIGEST_ARTIFACT
    if not src.is_file():
        return None
    dest_dir = run_dir(prefix)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / DIGEST_ARTIFACT
    shutil.copy2(src, dest)
    return dest


def persist_digest_json(prefix: str, digest: dict[str, Any]) -> Path:
    dest_dir = run_dir(prefix)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / DIGEST_ARTIFACT
    dest.write_text(json.dumps(digest, indent=2) + "\n", encoding="utf-8")
    return dest


def load_digest(prefix: str) -> dict[str, Any] | None:
    path = run_dir(prefix) / DIGEST_ARTIFACT
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_librarian_path(prefix: str) -> Path | None:
    path = run_dir(prefix) / LIBRARIAN_ARTIFACT
    return path if path.is_file() else None


def stage_librarian_for_workspace(
    prefix: str,
    workspace: Path,
    *,
    librarian_workspace: Path | None = None,
) -> Path | None:
    """Copy librarian.md into a downstream workspace before synthesizer dispatch."""
    workspace.mkdir(parents=True, exist_ok=True)
    dest = workspace / LIBRARIAN_ARTIFACT
    cached = load_librarian_path(prefix)
    if cached is not None:
        shutil.copy2(cached, dest)
        return dest
    if librarian_workspace is not None:
        src = librarian_workspace / LIBRARIAN_ARTIFACT
        if src.is_file():
            shutil.copy2(src, dest)
            return dest
    return None


def write_manifest(prefix: str, meta: dict[str, Any]) -> None:
    dest_dir = run_dir(prefix)
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
