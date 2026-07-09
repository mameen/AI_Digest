"""Test fixture paths — committed real network captures."""

from __future__ import annotations

from pathlib import Path

from lib.paths import REPO_ROOT


def fixture_path(name: str) -> Path:
    return REPO_ROOT / "tests" / "data" / name


def evaluation_fixture_path(name: str) -> Path:
    """Fixture-backed eval topic inputs under tests/data/evaluation/."""
    return REPO_ROOT / "tests" / "data" / "evaluation" / name


def resolve_fixture(name: str, *, evaluation: bool = False) -> Path:
    if evaluation:
        path = evaluation_fixture_path(name)
        if path.is_file():
            return path
    return fixture_path(name)
