"""Minimal run state representation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RunState:
    run_id: str
    phase: str = "ingest"
    notes: list[str] = field(default_factory=list)
