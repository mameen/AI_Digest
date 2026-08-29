"""Build a versioned ZIP package of the portable Orio skill.

Run from any working directory:
    python path/to/orio-ai-news-digest/scripts/build.py

The version is read from SKILL.md. Major and minor versions are never inferred
or changed by this script; only the supplied build timestamp belongs in the
third segment.
"""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_DIR / "SKILL.md"
BUILD_DIR = SKILL_DIR / ".build"
VERSION_RE = re.compile(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", re.MULTILINE)
SKIP_DIRS = {".build", ".git", "__pycache__"}
SKIP_SUFFIXES = {".pyc"}


def read_version() -> str:
    match = VERSION_RE.search(SKILL_MD.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError(f"version not found in {SKILL_MD}")
    return match.group(1)


def iter_files():
    for path in sorted(SKILL_DIR.rglob("*")):
        relative = path.relative_to(SKILL_DIR)
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        yield path, relative


def build() -> Path:
    version = read_version()
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    output = BUILD_DIR / f"orio-ai-news-digest-{version}.zip"
    if output.exists():
        output.unlink()

    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path, relative in iter_files():
            archive.write(path, Path(f"orio-ai-news-digest-{version}") / relative)
    return output


if __name__ == "__main__":
    artifact = build()
    print(f"built {artifact} ({artifact.stat().st_size:,} bytes)")
