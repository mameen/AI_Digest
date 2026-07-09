"""Format research bullets as researcher output.md."""

from __future__ import annotations

from pathlib import Path

from lib.ingest.types import ResearchBullet


def bullets_to_markdown(topic: str, bullets: list[ResearchBullet]) -> str:
    lines = [f"# Research: {topic}", ""]
    for bullet in bullets:
        status = "verified" if bullet.verified else "unverified"
        lines.append(f"- {bullet.title} ({status}): {bullet.url}")
    return "\n".join(lines) + "\n"


def write_research_markdown(topic: str, workspace: Path, bullets: list[ResearchBullet]) -> Path:
    workspace.mkdir(parents=True, exist_ok=True)
    out_path = workspace / "output.md"
    out_path.write_text(bullets_to_markdown(topic, bullets), encoding="utf-8")
    return out_path
