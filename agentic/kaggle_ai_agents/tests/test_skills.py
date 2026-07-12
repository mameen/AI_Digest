"""Tests for SKILL.md structure and script exit codes."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILLS_DIR = Path(__file__).parents[1] / "skills"
SRC_DIR = Path(__file__).parents[1] / "src"

REQUIRED_FRONTMATTER_FIELDS = {"name", "description"}

SKILLS_WITH_SCRIPTS = {
    "dedupe_and_rank": "scripts/rank.py",
    "artifact_validation": "scripts/validate.py",
    "baseline_eval": "scripts/evaluate.py",
}

# ── Fixtures ──────────────────────────────────────────────────────────────────

VALID_ITEMS = [
    {"source_id": "s1", "title": "Open model benchmarks improve",
     "url": "https://example.com/benchmarks", "summary": "Better results."},
    {"source_id": "s2", "title": "Agent tooling standards emerging",
     "url": "https://example.com/standards", "summary": "Less friction."},
    {"source_id": "dup", "title": "Open model benchmarks improve",
     "url": "https://example.com/benchmarks?ref=dup", "summary": "Duplicate."},
]

VALID_BRIEF = {
    "date": "2026-07-12",
    "theme": "AI signal",
    "cards": [{"rank": 1, "title": "Test story", "url": "https://example.com/test",
               "why_it_matters": "It matters."}],
}

INVALID_BRIEF = {"date": "2026-07-12"}  # missing required fields

VALID_INDEX = {
    "latest": "p1",
    "digests": [{"prefix": "p1", "story_count": 1, "avg_significance": 3.0}],
}


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    env = {"PYTHONPATH": str(SRC_DIR)}
    import os
    env.update(os.environ)
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True, text=True, env=env,
    )


# ── SKILL.md structure tests ──────────────────────────────────────────────────

def test_all_skills_have_skill_md() -> None:
    skill_dirs = [d for d in SKILLS_DIR.iterdir() if d.is_dir()]
    assert skill_dirs, "skills/ directory is empty"
    for skill_dir in skill_dirs:
        assert (skill_dir / "SKILL.md").exists(), f"Missing SKILL.md in {skill_dir.name}"


def test_all_skill_md_have_required_frontmatter() -> None:
    import re
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        assert match, f"{skill_dir.name}/SKILL.md has no YAML frontmatter block"
        import yaml
        fm = yaml.safe_load(match.group(1))
        missing = REQUIRED_FRONTMATTER_FIELDS - set(fm or {})
        assert not missing, f"{skill_dir.name}/SKILL.md missing fields: {missing}"


def test_skills_with_scripts_have_scripts_dir() -> None:
    for skill_name, script_rel in SKILLS_WITH_SCRIPTS.items():
        script_path = SKILLS_DIR / skill_name / script_rel
        assert script_path.exists(), f"Missing {script_path}"


# ── Script exit-code tests ────────────────────────────────────────────────────

def test_rank_script_succeeds_with_valid_input() -> None:
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(VALID_ITEMS, f)
        tmp = f.name
    result = _run(SKILLS_DIR / "dedupe_and_rank/scripts/rank.py", tmp)
    assert result.returncode == 0, result.stderr
    ranked = json.loads(result.stdout)
    assert len(ranked) <= 5
    assert ranked[0]["title"] == "Open model benchmarks improve"


def test_rank_script_fails_with_missing_file() -> None:
    result = _run(SKILLS_DIR / "dedupe_and_rank/scripts/rank.py", "/no/such/file.json")
    assert result.returncode == 1


def test_validate_script_succeeds_with_valid_brief() -> None:
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(VALID_BRIEF, f)
        tmp = f.name
    result = _run(SKILLS_DIR / "artifact_validation/scripts/validate.py", tmp)
    assert result.returncode == 0, result.stderr


def test_validate_script_fails_with_invalid_brief() -> None:
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(INVALID_BRIEF, f)
        tmp = f.name
    result = _run(SKILLS_DIR / "artifact_validation/scripts/validate.py", tmp)
    assert result.returncode == 1


def test_evaluate_script_succeeds_within_threshold() -> None:
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as bf:
        json.dump(VALID_BRIEF, bf)
        brief_tmp = bf.name
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as ix:
        json.dump(VALID_INDEX, ix)
        index_tmp = ix.name
    result = _run(SKILLS_DIR / "baseline_eval/scripts/evaluate.py", brief_tmp, index_tmp)
    assert result.returncode == 0, result.stderr


def test_evaluate_script_fails_when_exceeds_threshold() -> None:
    # Brief with 1 card vs baseline of 100 stories — guaranteed to fail threshold
    big_baseline = {
        "latest": "p1",
        "digests": [{"prefix": "p1", "story_count": 100, "avg_significance": 3.0}],
    }
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as bf:
        json.dump(VALID_BRIEF, bf)
        brief_tmp = bf.name
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as ix:
        json.dump(big_baseline, ix)
        index_tmp = ix.name
    result = _run(SKILLS_DIR / "baseline_eval/scripts/evaluate.py", brief_tmp, index_tmp)
    assert result.returncode == 1
