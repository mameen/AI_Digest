"""Tests for agentic/hermes/admin/skills_provider.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure Hermes root is on path so admin.skills_provider resolves consistently.
HERMES_ROOT = Path(__file__).resolve().parents[1]
if str(HERMES_ROOT) not in sys.path:
    sys.path.insert(0, str(HERMES_ROOT))

from admin.skills_provider import SkillEntry, SkillsProvider  # noqa: E402


# ---------------------------------------------------------------------------
# SkillEntry
# ---------------------------------------------------------------------------

class TestSkillEntry:
    def test_to_prompt_token_minimal(self):
        entry = SkillEntry(name="test-skill", description="A test skill", level=1)
        token = entry.to_prompt_token()
        assert "[skill:test-skill" in token
        assert "description=A test skill" in token

    def test_to_prompt_token_with_script_and_resources(self):
        entry = SkillEntry(
            name="full-skill",
            description="A full skill",
            level=4,
            script="scripts/run.py",
            resources=["ref1.md", "ref2.md"],
        )
        token = entry.to_prompt_token()
        assert "script=scripts/run.py" in token
        assert "resources=ref1.md,ref2.md" in token


# ---------------------------------------------------------------------------
# SkillsProvider — discovery
# ---------------------------------------------------------------------------

class TestSkillsProviderDiscovery:
    def test_from_paths_scans_directory(self, tmp_path: Path):
        """from_paths discovers SKILL.md files in the given directories."""
        skill_dir = tmp_path / "test_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: A discovered skill\nlevel: 3\n---\n",
            encoding="utf-8",
        )
        provider = SkillsProvider.from_paths([tmp_path])
        assert len(provider.skills) == 1
        assert provider.skills[0].name == "test-skill"

    def test_from_paths_skips_non_dirs(self, tmp_path: Path):
        """from_paths ignores non-directory entries."""
        (tmp_path / "not_a_dir").write_text("hello", encoding="utf-8")
        provider = SkillsProvider.from_paths([tmp_path])
        assert len(provider.skills) == 0

    def test_from_default_paths_returns_skills(self):
        """from_default_paths discovers skills from the default AI Digest directories."""
        provider = SkillsProvider.from_default_paths()
        names = {s.name for s in provider.skills}
        # We expect at least source-discovery to be found
        assert "source-discovery" in names

    def test_list_all_returns_dicts(self):
        """list_all returns a list of dicts with expected keys."""
        skill_dir = Path(__file__).resolve().parents[2] / "kaggle_ai_agents" / "skills" / "source_discovery"
        provider = SkillsProvider.from_paths([skill_dir])
        items = provider.list_all()
        assert len(items) >= 1
        item = items[0]
        assert "name" in item
        assert "description" in item
        assert "level" in item
        assert "status" in item


# ---------------------------------------------------------------------------
# SkillsProvider — role filtering
# ---------------------------------------------------------------------------

class TestSkillsProviderRoleFiltering:
    def test_filter_for_researcher_returns_two_skills(self):
        provider = SkillsProvider.from_default_paths()
        skills = provider.filter_for_role("RESEARCHER")
        names = {s.name for s in skills}
        assert "source-discovery" in names
        assert "dedupe-and-rank" in names

    def test_filter_for_librarian_returns_one_skill(self):
        provider = SkillsProvider.from_default_paths()
        skills = provider.filter_for_role("LIBRARIAN")
        names = {s.name for s in skills}
        assert "artifact-validation" in names

    def test_filter_for_synthesizer_returns_empty(self):
        provider = SkillsProvider.from_default_paths()
        skills = provider.filter_for_role("SYNTHESIZER")
        assert len(skills) == 0

    def test_filter_for_unknown_role_returns_empty(self):
        provider = SkillsProvider.from_default_paths()
        skills = provider.filter_for_role("UNKNOWN_ROLE")
        assert len(skills) == 0


# ---------------------------------------------------------------------------
# SkillsProvider — injection
# ---------------------------------------------------------------------------

class TestSkillsProviderInjection:
    def test_inject_for_researcher_adds_tokens(self):
        provider = SkillsProvider.from_default_paths()
        prompt = "## Instructions\nDo research."
        result = provider.inject_for_role("RESEARCHER", prompt)
        assert "[skill:source-discovery" in result
        assert "[skill:dedupe-and-rank" in result

    def test_inject_for_librarian_adds_token(self):
        provider = SkillsProvider.from_default_paths()
        prompt = "## Instructions\nMerge articles."
        result = provider.inject_for_role("LIBRARIAN", prompt)
        assert "[skill:artifact-validation" in result

    def test_inject_for_synthesizer_returns_unchanged(self):
        provider = SkillsProvider.from_default_paths()
        prompt = "## Instructions\nSynthesize digest."
        result = provider.inject_for_role("SYNTHESIZER", prompt)
        assert result == prompt  # No skills for synthesizer

    def test_inject_inserts_before_instructions_header(self):
        provider = SkillsProvider.from_default_paths()
        prompt = "Some preamble\n## Instructions\nDo work."
        result = provider.inject_for_role("RESEARCHER", prompt)
        # Injection should appear before ## Instructions
        assert result.index("[skill:") < result.index("## Instructions")


# ---------------------------------------------------------------------------
# SkillsProvider — error handling
# ---------------------------------------------------------------------------

class TestSkillsProviderErrorHandling:
    def test_from_paths_with_missing_dir(self):
        """from_paths handles missing directories gracefully."""
        provider = SkillsProvider.from_paths([Path("/nonexistent/path/that/does/not/exist")])
        assert len(provider.skills) == 0

    def test_inject_handles_empty_provider(self):
        """inject_for_role works even with an empty provider."""
        provider = SkillsProvider()
        prompt = "## Instructions\nDo work."
        result = provider.inject_for_role("RESEARCHER", prompt)
        assert result == prompt  # No skills to inject
