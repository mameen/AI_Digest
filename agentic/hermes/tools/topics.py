"""Demo research topics — board, showcase, and provenance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from lib.ingest.topics.registry import SourceKind, binding_for
from lib.paths import AGENTIC_ROOT
from llm_pipeline.editorial import CANONICAL_ORDER
from llm_pipeline.grounding import collect_roots
from llm_pipeline.validate import validate_digest

_DEFAULT_TOPICS = ("aisearch", "leaderboard", "youtube")

_ROLES_PATH = Path(__file__).resolve().parents[1] / "admin" / "config" / "hermes_roles.yaml"

_AUTO_TOPIC_TOKENS = frozenset({"auto", "best", "best_report"})


def _load_roles_spec() -> dict[str, Any]:
    if not _ROLES_PATH.is_file():
        return {}
    return yaml.safe_load(_ROLES_PATH.read_text(encoding="utf-8")) or {}


def _reports_dir() -> Path:
    return AGENTIC_ROOT / "reports"


def _report_json_paths(reports_dir: Path | None = None) -> list[Path]:
    root = reports_dir or _reports_dir()
    if not root.is_dir():
        return []
    return sorted(
        p
        for p in root.glob("*.json")
        if p.name != "index.json" and len(p.stem) == 14 and p.stem.isdigit()
    )


def _digest_story_total(digest: dict[str, Any]) -> int:
    return sum(
        len(c.get("stories") or [])
        for c in (digest.get("categories") or [])
        if isinstance(c, dict)
    )


def _category_ids_from_digest(digest: dict[str, Any]) -> list[str]:
    """Category ids with at least one story, in canonical digest order."""
    counts: dict[str, int] = {}
    for cat in digest.get("categories") or []:
        if not isinstance(cat, dict):
            continue
        cid = str(cat.get("id") or "").strip()
        if not cid:
            continue
        counts[cid] = len(cat.get("stories") or [])

    ordered = [cid for cid in CANONICAL_ORDER if counts.get(cid, 0) > 0]
    for cid, n in counts.items():
        if n > 0 and cid not in ordered:
            ordered.append(cid)
    return ordered


def _goodness_from_errors(errors: list[str]) -> str:
    if not errors:
        return "pass"
    blocking = any(
        "story count" in e
        or e.startswith("missing required category")
        or e.startswith("missing summary")
        or e.startswith("ungrounded")
        for e in errors
    )
    return "fail" if blocking else "warn"


def best_known_good_report(
    *,
    reports_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Pick the passing/warn report with the highest story count."""
    from tools.baseline import agentic_config, validation_roots

    cfg = agentic_config()
    best: tuple[int, int, str, dict[str, Any], str] | None = None

    for path in _report_json_paths(reports_dir):
        try:
            digest = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        prefix = str(digest.get("filename_prefix") or path.stem)
        errors = validate_digest(cfg, digest, validation_roots(cfg, prefix))
        if _goodness_from_errors(errors) == "fail":
            continue
        total = _digest_story_total(digest)
        if total <= 0:
            continue
        prefix = str(digest.get("filename_prefix") or path.stem)
        cat_count = len(_category_ids_from_digest(digest))
        score = (total, cat_count, prefix)
        if best is None or score > (best[0], best[1], best[2]):
            best = (total, cat_count, prefix, digest, _goodness_from_errors(errors))

    if not best:
        return None
    total, cat_count, prefix, digest, goodness = best
    return {
        "prefix": prefix,
        "digest": digest,
        "story_total": total,
        "category_count": cat_count,
        "goodness": goodness,
        "topics": _category_ids_from_digest(digest),
        "report_json": str((_reports_dir() / f"{prefix}.json").resolve()),
    }


def _explicit_demo_topics(roles: dict[str, Any]) -> list[str] | None:
    raw = roles.get("demo_topics")
    if not raw:
        return None
    if isinstance(raw, str) and raw.strip().lower() in _AUTO_TOPIC_TOKENS:
        return None
    if len(raw) == 1 and str(raw[0]).strip().lower() in _AUTO_TOPIC_TOKENS:
        return None
    topics = [str(t).strip().lower() for t in raw if str(t).strip()]
    return topics or None


def resolve_board_topics(roles: dict[str, Any] | None = None) -> dict[str, Any]:
    """Board topic list + provenance (explicit yaml override or best report)."""
    spec = roles if roles is not None else _load_roles_spec()
    pinned = _explicit_demo_topics(spec)
    if pinned:
        return {
            "topics": pinned,
            "source": "hermes_roles.yaml",
            "source_prefix": None,
            "story_total": None,
            "goodness": None,
        }

    best = best_known_good_report()
    if best:
        return {
            "topics": best["topics"],
            "source": "best_known_good_report",
            "source_prefix": best["prefix"],
            "story_total": best["story_total"],
            "goodness": best["goodness"],
            "report_json": best["report_json"],
        }

    return {
        "topics": list(_DEFAULT_TOPICS),
        "source": "default_fallback",
        "source_prefix": None,
        "story_total": None,
        "goodness": None,
    }


def load_demo_topics(roles: dict[str, Any] | None = None) -> list[str]:
    if roles is not None:
        pinned = _explicit_demo_topics(roles)
        if pinned:
            return pinned
        if roles.get("demo_topics"):
            # non-empty but auto token handled above; fall through if empty list
            pass
        elif "demo_topics" in roles:
            return resolve_board_topics(roles)["topics"]
    return resolve_board_topics(None)["topics"]


def research_category_ids(roles: dict[str, Any] | None = None) -> frozenset[str]:
    return frozenset(load_demo_topics(roles))


def research_task_body(topic: str, *, prefix: str) -> str:
    """Kanban task body for a researcher worker — driven by topic registry."""
    binding = binding_for(topic)
    tool_lines = [
        "- `read_topic_config` (digest) — source binding for this topic",
        "- Hermes `web_search` (ddgs) to discover URLs when needed",
        "- `verify_url` (digest) on every URL before citing",
    ]
    if binding:
        if SourceKind.PREFLIGHT_CATEGORY in binding.kinds:
            cat = binding.preflight_category or binding.topic_id
            tool_lines.insert(
                1,
                f"- `read_preflight_category` (digest) category `{cat}` — lazy fetch on cache miss",
            )
        if SourceKind.RSS_FEEDS in binding.kinds:
            tool_lines.insert(
                -1,
                "- `fetch_rss` (digest) — omit feeds to use topic defaults",
            )
        if SourceKind.CRAWL_MARKDOWN in binding.kinds and binding.crawl_slugs:
            slug = binding.crawl_slugs[0]
            tool_lines.insert(
                -1,
                f"- `read_crawl_markdown` (digest) slug `{slug}` — lazy crawl on cache miss",
            )
        if SourceKind.STRUCTURED_JSON in binding.kinds and binding.structured_slugs:
            slug = binding.structured_slugs[0]
            tool_lines.insert(
                -1,
                f"- `read_structured_json` (digest) slug `{slug}` — lazy fetch on cache miss",
            )
    else:
        tool_lines.insert(
            1,
            f"- `read_preflight_category` (digest) category `{topic}` — if preflight exists",
        )

    rubric = ""
    if binding and binding.rubric:
        rubric = f"\n\nTopic rubric: {binding.rubric}"

    return (
        f"Research **{topic}** for AI Digest (run prefix `{prefix}`).\n\n"
        f"**Step 1 (mandatory):** call `read_topic_config` with `topic` = `{topic}`.\n"
        f"**Step 2:** call `read_preflight_category` with `category_id` = `{topic}` "
        f"and `prefix` = `{prefix}` when the topic config lists preflight.\n\n"
        "Then gather sources:\n"
        + "\n".join(tool_lines)
        + "\n\nWrite **output.md** in your workspace: 3+ bullet lines, each with a "
        "verified `http` URL and a short summary. **Reflect** on coverage and gaps in "
        "your kanban_complete summary. **You own grounding for this target** — "
        "Librarian and Synthesizer trust your artifact; they do not re-fetch or "
        "re-verify your links. Handle errors (retry search, note gaps) — do not invent links."
        + rubric
        + "\n\n**Never call `kanban_block` for unknown topic** — the topic is "
        f"`{topic}`; retry tools with that id.\n\n"
        "Finish with `kanban_complete` with "
        'artifacts: ["<absolute-path>/output.md"]. '
        "Do not call kanban_block unless an external dependency is truly unavailable."
    )
