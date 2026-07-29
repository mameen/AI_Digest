"""SkillsProvider — discover and inject agentskills.io-aligned skills into kanban workers.

Wraps ``agentic/kaggle_ai_agents/skills/`` directories via discovery methods like
``from_paths()``. At dispatch time, each role gets its relevant skills injected into
the task system prompt as progressive-discovery tokens rather than raw SOUL text.

Usage::

    from admin.skills_provider import SkillsProvider

    provider = SkillsProvider.from_default_paths()
    researcher_skills = provider.filter_for_role("RESEARCHER")
    # → [{"name": "source-discovery", "description": "...", "resources": [...]}, ...]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillEntry:
    """A single skill discovered from a SKILL.md file."""

    name: str
    description: str
    level: int
    script: str | None = None
    resources: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    status: str = "📋 Stub"
    raw_path: Path | None = None

    def to_prompt_token(self) -> str:
        """Return a progressive-discovery token for kanban dispatch injection."""
        parts = [f"[skill:{self.name}"]
        if self.description:
            parts.append(f"description={self.description[:120]}")
        if self.script:
            parts.append(f"script={self.script}")
        if self.resources:
            parts.append(f"resources={','.join(self.resources)}")
        parts.append("]")
        return "".join(parts)


@dataclass
class SkillsProvider:
    """Discovers skills from SKILL.md files and provides role-based filtering."""

    skills: list[SkillEntry] = field(default_factory=list)
    _source_dirs: list[Path] = field(default_factory=list, repr=False)

    # Role → skill name mapping (which skills each kanban worker needs)
    ROLE_SKILLS: dict[str, list[str]] = field(default_factory=lambda: {
        "RESEARCHER": ["source-discovery", "dedupe-and-rank"],
        "LIBRARIAN": ["artifact-validation"],
        "SYNTHESIZER": [],  # Synthesizer doesn't need a separate skill set
        "CONCIERGE": [],  # Concierge is orchestration-only
    })

    @classmethod
    def from_paths(cls, paths: list[Path]) -> SkillsProvider:
        """Discover skills by scanning SKILL.md files in the given directories."""
        provider = cls()
        for path in paths:
            if not path.is_dir():
                continue
            provider._source_dirs.append(path)
            _scan_directory(path, provider.skills)
        return provider

    @classmethod
    def from_default_paths(cls) -> SkillsProvider:
        """Discover skills from the default AI Digest skill directories."""
        repo = Path(__file__).resolve().parents[4]  # Go up to repo root
        paths = [
            repo / "agentic" / "kaggle_ai_agents" / "skills",
            repo / "agentic" / "docs",
        ]
        return cls.from_paths(paths)

    def filter_for_role(self, role: str) -> list[SkillEntry]:
        """Return skills relevant to the given kanban worker role."""
        skill_names = self.ROLE_SKILLS.get(role, [])
        if not skill_names:
            return []
        name_set = set(skill_names)
        return [s for s in self.skills if s.name in name_set]

    def inject_for_role(self, role: str, system_prompt: str) -> str:
        """Inject skill tokens into a kanban worker's system prompt."""
        skills = self.filter_for_role(role)
        if not skills:
            return system_prompt
        tokens = "\n".join(s.to_prompt_token() for s in skills)
        injection = f"\n## Active Skills\n{tokens}\n"
        # Insert before the last section header or at the end
        if "## Instructions" in system_prompt:
            return system_prompt.replace(
                "## Instructions",
                f"{injection}## Instructions",
            )
        return system_prompt + injection

    def list_all(self) -> list[dict[str, Any]]:
        """Return all discovered skills as dicts for diagnostics/telemetry."""
        return [
            {
                "name": s.name,
                "description": s.description[:80],
                "level": s.level,
                "status": s.status,
                "script": s.script,
            }
            for s in self.skills
        ]


def _scan_directory(dirpath: Path, out: list[SkillEntry]) -> None:
    """Scan a directory for SKILL.md files and parse them into SkillEntry objects."""
    for skill_dir in sorted(dirpath.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            # Also check the directory itself as a SKILL.md
            skill_md = skill_dir
            if not skill_md.is_file() or skill_md.name != "SKILL.md":
                continue

        content = skill_md.read_text(encoding="utf-8")
        entry = _parse_skill_md(content, skill_md)
        if entry:
            out.append(entry)


def _parse_skill_md(content: str, path: Path) -> SkillEntry | None:
    """Parse a SKILL.md file into a SkillEntry."""
    # Extract frontmatter
    name = ""
    description = ""
    level = 0
    script = None

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm = _parse_yaml_frontmatter(parts[1])
            name = fm.get("name", "")
            description = fm.get("description", "")
            level = int(fm.get("level", 0))

    # Fallback: extract name from heading
    if not name:
        match = re.search(r"^#\s+(\S+)", content, re.MULTILINE)
        if match:
            name = match.group(1)

    # Extract script path
    script_match = re.search(r"script:\s*\[([^\]]+)\]", content)
    if script_match:
        script = script_match.group(1).strip()

    # Extract resources
    resources = []
    res_match = re.search(r"resources:\s*\[([^\]]*)\]", content)
    if res_match:
        resources = [r.strip().strip('"').strip("'") for r in res_match.group(1).split(",") if r.strip()]

    # Extract status emoji
    status = "📋 Stub"
    status_match = re.search(r"status:\s*([^\n]+)", content)
    if status_match:
        status = status_match.group(1).strip()

    return SkillEntry(
        name=name,
        description=description or f"Skill located at {path.relative_to(path.parents[2])}",
        level=level,
        script=script,
        resources=resources,
        raw_path=path,
        status=status,
    )


def _parse_yaml_frontmatter(text: str) -> dict[str, Any]:
    """Minimal YAML frontmatter parser (no external deps)."""
    result: dict[str, Any] = {}
    for line in text.strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if value:
                result[key] = value
    return result
