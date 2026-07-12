"""Shared helpers for digest report HTML / index generation."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
SKILL_DIR = SCRIPTS_DIR.parent
PROJECT_DIR = SKILL_DIR.parent.parent
REPORTS_DIR = PROJECT_DIR / "reports"

CONTENT_TEMPLATE = SKILL_DIR / "content.template.html"
FRAME_TEMPLATE = SKILL_DIR / "frame.html"
DIGEST_APP = SKILL_DIR / "digest-app.js"


def normalize_prefix(stem: str, generated_at: str | None = None) -> str | None:
    """Return a 14-digit YYYYMMDDHHMMSS prefix, padding seconds when needed."""
    if not stem.isdigit():
        return None
    if len(stem) == 14:
        return stem
    if len(stem) == 12:
        if generated_at:
            try:
                dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                return dt.strftime("%Y%m%d%H%M%S")
            except ValueError:
                pass
        return stem + "00"
    return None


def fix_missing_mmss(reports_dir: Path | None = None) -> list[tuple[str, str]]:
    """Rename 12-digit digest stems to 14-digit (fill missing SS). Returns [(old, new), ...]."""
    root = reports_dir or REPORTS_DIR
    fixes: list[tuple[str, str]] = []
    for path in sorted(root.glob("*.json")):
        if path.name == "index.json":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        new_stem = normalize_prefix(path.stem, data.get("generated_at"))
        if new_stem is None or new_stem == path.stem:
            continue
        new_json = root / f"{new_stem}.json"
        if new_json.exists():
            raise RuntimeError(f"Cannot rename {path.name}: {new_json.name} already exists")

        data["filename_prefix"] = new_stem
        new_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        path.unlink()

        old_html = root / f"{path.stem}.html"
        new_html = root / f"{new_stem}.html"
        if old_html.exists():
            if new_html.exists():
                old_html.unlink()
            else:
                old_html.rename(new_html)

        fixes.append((path.stem, new_stem))
    return fixes


def list_digest_jsons(reports_dir: Path | None = None) -> list[Path]:
    root = reports_dir or REPORTS_DIR
    return sorted(
        p for p in root.glob("*.json")
        if p.name != "index.json" and len(p.stem) == 14 and p.stem.isdigit()
    )


def story_stats(data: dict) -> tuple[int, float, dict[str, int]]:
    counts = dict(data.get("visualizations", {}).get("category_counts") or {})
    stories: list[dict] = []
    for cat in data.get("categories", []):
        for story in cat.get("stories", []):
            stories.append(story)
            cid = cat.get("id", "")
            if cid and cid not in counts:
                counts[cid] = counts.get(cid, 0) + 1
    if not stories and counts:
        story_count = sum(counts.values())
    else:
        story_count = len(stories)
    if stories:
        avg_sig = round(sum(s.get("significance", 0) for s in stories) / len(stories), 1)
    else:
        avg_sig = 0.0
    return story_count, avg_sig, counts


def digest_index_entry(data: dict, prefix: str) -> dict:
    story_count, avg_sig, counts = story_stats(data)
    generated = data.get("generated_at") or ""
    if generated:
        date = generated[:10]
    else:
        date = f"{prefix[:4]}-{prefix[4:6]}-{prefix[6:8]}"
    dt = datetime.fromisoformat(generated.replace("Z", "+00:00")) if generated else None
    display_date = (
        dt.strftime("%A, %B %d, %Y").upper()
        if dt
        else datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d, %Y").upper()
    )
    return {
        "prefix": prefix,
        "date": date,
        "display_date": display_date,
        "summary": data.get("summary", ""),
        "story_count": story_count,
        "avg_significance": avg_sig,
        "categories": counts,
        "report_source": data.get("report_source"),
        "report_source_label": data.get("report_source_label"),
    }


def build_index(reports_dir: Path | None = None) -> dict:
    root = reports_dir or REPORTS_DIR
    entries: list[dict] = []
    by_date: dict[str, dict] = {}
    for path in list_digest_jsons(root):
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = digest_index_entry(data, path.stem)
        entries.append(entry)
        prev = by_date.get(entry["date"])
        if not prev or entry["prefix"] > prev["prefix"]:
            by_date[entry["date"]] = entry
    entries.sort(key=lambda e: e["prefix"])
    latest = entries[-1]["prefix"] if entries else None
    return {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latest": latest,
        "digests": entries,
        "by_date": list(by_date.values()),
    }


def find_line(lines: list[str], starts_with: str) -> int:
    for i, line in enumerate(lines):
        if line.strip().startswith(starts_with):
            return i
    raise RuntimeError(f"Could not find line starting with: {starts_with!r}")


def extract_leaderboards(html: str) -> str | None:
    marker = "const leaderboards = "
    start = html.find(marker)
    if start < 0:
        return None
    start += len(marker)
    depth = 0
    in_str = False
    escape = False
    quote = ""
    i = start
    while i < len(html):
        ch = html[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                in_str = False
        else:
            if ch in "\"'":
                in_str = True
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return html[start : i + 1]
        i += 1
    return None


def default_leaderboards_block(template_text: str | None = None) -> str:
    if template_text is None:
        legacy = SKILL_DIR / "template.html"
        template_text = legacy.read_text(encoding="utf-8")
    return extract_leaderboards(template_text) or "{}"


def leaderboards_for_prefix(prefix: str, reports_dir: Path | None = None) -> str:
    root = reports_dir or REPORTS_DIR
    html_path = root / f"{prefix}.html"
    if html_path.exists():
        block = extract_leaderboards(html_path.read_text(encoding="utf-8"))
        if block:
            return block
    return default_leaderboards_block()


def content_styles_block() -> str:
    from llm_pipeline.styles import digest_styles

    return digest_styles()


def frame_styles_block() -> str:
    from llm_pipeline.styles import frame_styles

    return frame_styles()


def content_panel_block() -> str:
    text = CONTENT_TEMPLATE.read_text(encoding="utf-8")
    start = text.index('<div class="masthead">')
    end = text.index('<div class="d3-tooltip"', start)
    panel = text[start:end]
    panel = re.sub(r'\s*<span class="masthead-archive">.*?</span>\s*', "", panel, flags=re.DOTALL)
    panel = panel.replace('<div class="content-loading">Loading digest…</div>', "")
    return f'<div id="digest-panel">\n{panel.strip()}\n</div>'


def digest_app_js() -> str:
    return DIGEST_APP.read_text(encoding="utf-8")


def theme_js() -> str:
    from llm_pipeline.styles import theme_script

    return theme_script()


def theme_apply_js() -> str:
    from llm_pipeline.styles import theme_apply_script

    return theme_apply_script()


def trend_charts_js() -> str:
    from llm_pipeline.styles import trend_charts_script

    return trend_charts_script()


def heatmap_js() -> str:
    from llm_pipeline.styles import heatmap_script

    return heatmap_script()


def build_frame_html(reports_dir: Path | None = None) -> str:
    """Render index.html: collapsible heatmap + latest digest loaded inline."""
    root = reports_dir or REPORTS_DIR
    index_path = root / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Missing sibling index.json for index.html: {index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    digests: dict[str, dict] = {}
    for entry in index.get("digests", []):
        prefix = entry["prefix"]
        digests[prefix] = json.loads((root / f"{prefix}.json").read_text(encoding="utf-8"))
    latest = index.get("latest") or (index.get("digests") or [{}])[-1].get("prefix")
    lb = leaderboards_for_prefix(latest, root) if latest else default_leaderboards_block()

    template = FRAME_TEMPLATE.read_text(encoding="utf-8")
    replacements = {
        "__FRAME_STYLES__": frame_styles_block(),
        "__CONTENT_STYLES__": content_styles_block(),
        "__THEME_JS__": theme_js(),
        "__HEATMAP_JS__": heatmap_js(),
        "__TREND_CHARTS_JS__": trend_charts_js(),
        "__CONTENT_PANEL__": content_panel_block(),
        "__INDEX_SCRIPT__": f"<script>window.__AIDIGEST_INDEX__ = {json.dumps(index, ensure_ascii=False)};</script>",
        "__DIGESTS_SCRIPT__": f"<script>window.__AIDIGEST_DIGESTS__ = {json.dumps(digests, ensure_ascii=False)};</script>",
        "__LEADERBOARDS__": lb,
        "__DIGEST_APP__": digest_app_js(),
    }
    html = template
    for key, value in replacements.items():
        if key not in html:
            raise RuntimeError(f"frame.html missing {key}")
        html = html.replace(key, value)
    if "__AUTHOR_CARD__" in html:
        from llm_pipeline.config import load_config
        from llm_pipeline.frame_author import inject_author_card

        html = inject_author_card(html, load_config())
    from llm_pipeline.frame_html import assert_archive_html_ready

    assert_archive_html_ready(html)
    return html


def build_content_html(prefix: str, leaderboards_json: str, template_text: str | None = None) -> str:
    template = template_text or CONTENT_TEMPLATE.read_text(encoding="utf-8")
    json_path = REPORTS_DIR / f"{prefix}.json"
    if not json_path.exists():
        raise FileNotFoundError(json_path)
    payload = json_path.read_text(encoding="utf-8").strip()
    html = (
        template.replace("__PREFIX__", prefix)
        .replace("__LEADERBOARDS__", leaderboards_json)
        .replace("__DIGEST_JSON__", payload)
        .replace("__DIGEST_APP__", digest_app_js())
        .replace("__STYLES__", content_styles_block())
        .replace("__THEME_JS__", theme_apply_js())
    )
    if "__PREFIX__" in html or "__LEADERBOARDS__" in html or "__DIGEST_JSON__" in html or "__DIGEST_APP__" in html:
        raise RuntimeError("content template placeholders were not fully replaced")
    if "__STYLES__" in html or "__THEME_JS__" in html:
        raise RuntimeError("content template style placeholders were not fully replaced")
    return html
