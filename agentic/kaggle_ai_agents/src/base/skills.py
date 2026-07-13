"""Skill/Tool interface for agent implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Skill(ABC):
    """Base class for all skills (tools) used by agents.
    
    A Skill is a callable tool that agents use to accomplish tasks.
    Examples: discover_stories, rank_stories, validate_brief.
    """

    name: str = "unnamed_skill"
    description: str = "A generic skill"

    @abstractmethod
    def __call__(self, *args, **kwargs) -> Any:
        """Execute the skill.
        
        Returns:
            Skill-specific output (list, dict, object, etc.)
        
        Raises:
            Exception: If skill execution fails
        """
        pass

    def to_dict(self) -> Dict[str, str]:
        """Export skill metadata for agent registration."""
        return {
            "name": self.name,
            "description": self.description,
        }
