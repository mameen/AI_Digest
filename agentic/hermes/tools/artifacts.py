"""Artifact validation and digest assembly for agentic Hermes workers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

RESEARCH_ARTIFACT = "output.md"
LIBRARIAN_ARTIFACT = "librarian.md"
DIGEST_ARTIFACT = "digest.json"


def validate_researcher_artifact(workspace: Path) -> list[str]:
    """Return validation errors; empty list means output.md is acceptable."""
    path = workspace / RESEARCH_ARTIFACT
    if not path.is_file():
        return [f"missing {path}"]
    text = path.read_text(encoding="utf-8")
    if len(text.strip()) < 40:
        return ["output.md too short"]
    if len(re.findall(r"https?://", text)) < 2:
        return ["output.md needs at least 2 URLs"]
    bullets = [ln for ln in text.splitlines() if ln.strip().startswith("-")]
    if len(bullets) < 3:
        return ["output.md needs at least 3 bullet lines"]
    return []


def _research_topic(title: str) -> str:
    if title.lower().startswith("research:"):
        return title.split(":", 1)[1].strip()
    return title.strip()


def _read_research_output(
    row: dict[str, Any],
    *,
    prefix: str | None = None,
    hermes_home: Path | None = None,
) -> str | None:
    """Read researcher output.md from workspace or runtime cache."""
    home = hermes_home or Path.home() / ".hermes"
    ws_path = row.get("workspace_path")
    ws = Path(ws_path) if ws_path else home / "kanban" / "workspaces" / row["id"]
    if not validate_researcher_artifact(ws):
        return (ws / RESEARCH_ARTIFACT).read_text(encoding="utf-8")
    if prefix:
        from tools.runtime_store import load_research_text

        topic = _research_topic(str(row.get("title", "")))
        return load_research_text(prefix, topic)
    return None


def validate_librarian_artifact(workspace: Path) -> list[str]:
    path = workspace / LIBRARIAN_ARTIFACT
    if not path.is_file():
        return [f"missing {path}"]
    text = path.read_text(encoding="utf-8")
    if len(text.strip()) < 80:
        return ["librarian.md too short"]
    if text.count("##") < 2:
        return ["librarian.md needs section headings"]
    if len(re.findall(r"https?://", text)) < 2:
        return ["librarian.md needs at least 2 URLs"]
    return []


def validate_synthesizer_artifact(workspace: Path) -> list[str]:
    path = workspace / DIGEST_ARTIFACT
    if not path.is_file():
        return [f"missing {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"digest.json invalid JSON: {exc}"]
    if not str(data.get("summary") or "").strip():
        return ["digest.json missing summary"]
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        return ["digest.json needs categories[]"]
    if len(categories) < 12:
        return [f"digest.json needs 12 categories, got {len(categories)}"]
    stories = sum(len(c.get("stories") or []) for c in categories if isinstance(c, dict))
    if stories < 20:
        return [f"digest.json needs at least 20 stories, got {stories}"]
    return []


def _citation_url_ok(url: str | None, *, verified: bool) -> bool:
    """Reject bare domains and unverified URLs for stable citations."""
    if not url or not verified:
        return False
    return _story_url_ok(url)


def _story_url_ok(url: str | None) -> bool:
    """Reject bare-domain URLs unsuitable as story citations."""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    return bool((parsed.path or "").strip("/"))


def _clean_bullet_line(bullet: str) -> tuple[str, str | None]:
    """Return (title, url) from a research bullet line."""
    urls = re.findall(r"https?://[^\s\)>\"%]+", bullet)
    url = urls[0].rstrip("%C2%A0") if urls else None
    title = bullet
    title = re.sub(r"\s*\((?:un)?verified\)\s*:\s*https?://\S+", "", title, flags=re.I)
    title = re.sub(r"\s*:\s*https?://\S+", "", title)
    title = title.strip() or (url or "Update")
    if len(title) > 120:
        title = title[:117] + "..."
    return title, url


def _parse_bullet_stories(text: str, topic: str) -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    idx = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        bullet = stripped.lstrip("-").strip()
        if not bullet:
            continue
        title, url = _clean_bullet_line(bullet)
        if url and not _story_url_ok(url):
            continue
        stories.append(
            {
                "id": f"agent-{topic.replace(' ', '-')}-{idx + 1}",
                "title": title,
                "summary": bullet,
                "source": "Researcher",
                "url": url,
                "significance": 3,
                "novelty": 3,
                "relevance_design": 2,
                "tags": [topic],
                "provenance": f"agent:researcher:{topic}",
            }
        )
        idx += 1
    return stories


def assemble_digest_from_research(
    research_rows: list[dict[str, Any]],
    *,
    prefix: str | None = None,
    hermes_home: Path | None = None,
) -> dict[str, Any]:
    """Build minimal digest JSON from done researcher output.md files."""
    home = hermes_home or Path.home() / ".hermes"
    run_prefix = prefix or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    categories: list[dict[str, Any]] = []
    topic_labels = {
        "aisearch": ("aisearch", "AI Search & Video", "🔍"),
        "leaderboard": ("leaderboard", "Leaderboard Rankings", "🏆"),
        "robotics": ("robotics", "Robotics", "🤖"),
        "llm": ("llm", "LLMs & Reasoning", "🧠"),
        "rag": ("rag", "RAG & Retrieval", "📚"),
    }

    for row in research_rows:
        ws_path = row.get("workspace_path")
        ws = Path(ws_path) if ws_path else home / "kanban" / "workspaces" / row["id"]
        out = ws / RESEARCH_ARTIFACT
        if not out.is_file() or validate_researcher_artifact(ws):
            continue
        topic = _research_topic(str(row.get("title", "")))
        stories = _parse_bullet_stories(out.read_text(encoding="utf-8"), topic)
        if not stories:
            continue
        cat_id, label, icon = topic_labels.get(topic, (topic, topic.title(), "📰"))
        categories.append({"id": cat_id, "label": label, "icon": icon, "stories": stories})

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "generated_at": generated_at,
        "filename_prefix": run_prefix,
        "summary": (
            "Agentic Hermes POC digest assembled from parallel researcher artifacts "
            f"({len(categories)} categories)."
        ),
        "categories": categories,
    }


def seed_research_artifact(
    topic: str,
    workspace: Path,
    *,
    cfg: dict[str, Any] | None = None,
    prefix: str | None = None,
) -> dict[str, Any]:
    """Test/eval helper — compose output.md from registry bindings (not for live workers)."""
    from tools.researchers import seed_topic

    return seed_topic(topic, workspace, cfg=cfg, prefix=prefix)


def seed_librarian_artifact(
    research_rows: list[dict[str, Any]],
    workspace: Path,
    *,
    prefix: str | None = None,
    hermes_home: Path | None = None,
    cfg: dict[str, Any] | None = None,
    roles: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge researcher output.md files into librarian.md."""
    home = hermes_home or Path.home() / ".hermes"
    workspace.mkdir(parents=True, exist_ok=True)
    lines = ["# Librarian: merge & classify", "", "## Topics applied", ""]
    topics: list[str] = []

    for row in research_rows:
        topic = _research_topic(str(row.get("title", "")))
        text = _read_research_output(row, prefix=prefix, hermes_home=home)
        if not text:
            continue
        topics.append(topic)
        lines.append(f"- **{topic}** ← research/{topic}.md")
    lines.extend(["", "## Merged research", ""])
    for row in research_rows:
        topic = _research_topic(str(row.get("title", "")))
        text = _read_research_output(row, prefix=prefix, hermes_home=home)
        if not text:
            continue
        lines.append(f"### {topic}")
        lines.append(text.strip())
        lines.append("")
    lines.extend(
        [
            "## Graph sketch",
            "",
            "- `feeds_topic`: each research topic → standing category",
            "- `related_to`: cross-topic links TBD by synthesizer",
            "",
        ]
    )
    out_path = workspace / LIBRARIAN_ARTIFACT
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if not topics:
        return {"ok": False, "path": str(out_path), "topics": topics, "topic_count": 0}

    if cfg and roles:
        from tools.enrich import enrich_cfg, enrich_librarian_md

        ecfg = enrich_cfg(cfg, roles)
        if ecfg:
            result = enrich_librarian_md(
                workspace, research_rows, ecfg, prefix=prefix, hermes_home=home
            )
            for warning in result.warnings:
                print(f"  enrich: {warning}")

    ok = not validate_librarian_artifact(workspace)
    return {"ok": ok, "path": str(out_path), "topics": topics, "topic_count": len(topics)}



def load_digest_from_synthesizer_workspace(workspace: Path) -> dict[str, Any] | None:
    path = workspace / DIGEST_ARTIFACT
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
