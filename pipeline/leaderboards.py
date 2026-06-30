"""Parse crawled leaderboard markdown into table rows.

Keeps the rendered leaderboard widget in sync with the live crawl instead of the
stale hand-coded constants in ``template.html``. Currently drives the AA
Intelligence table (``aa``); the block-editing helpers are source-agnostic so
additional tables can be wired in the same way.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

AA_CRAWL_SLUG = "artificialanalysis.ai_leaderboards_models.md"
ARENA_T2I_CRAWL_SLUG = "arena.ai_leaderboard_text-to-image.md"

_IMG_MD = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_WEB_SEARCH = re.compile(r"\s*\[web-search\]")
_MD_LINK = re.compile(r"\[([^\]]+)\]\(")


# ── crawl markdown → structured rows ─────────────────────────────────────────
def parse_aa_models_md(md: str) -> list[dict[str, Any]]:
    """Extract data rows from the AA LLM intelligence leaderboard table."""
    out: list[dict[str, Any]] = []
    for line in md.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 9 or "[Model]" not in cells[-1]:
            continue
        model = cells[0]
        provider = _IMG_MD.sub("", cells[2]).strip()
        intel = cells[3].rstrip("*").strip()
        if not model or not provider:
            continue
        try:
            intel_val = int(intel)
        except ValueError:
            continue
        out.append({
            "model": model,
            "context": cells[1],
            "provider": provider,
            "intelligence": intel_val,
            "price": cells[4],
            "speed": cells[5],
            "latency": cells[6],
        })
    return out


def parse_arena_image_md(md: str) -> list[dict[str, Any]]:
    """Extract rows from the arena.ai Text-to-Image leaderboard table.

    Each model cell looks like ``[<id>](<url> "<title>") <Provider> · <License>``
    (sometimes with a leading brand word and a ``[web-search]`` tag); the
    provider is the text between the link's closing paren and the ``·``.
    """
    out: list[dict[str, Any]] = []
    for line in md.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 5 or not cells[0].isdigit():
            continue
        model_cell = _WEB_SEARCH.sub("", cells[2])
        m = _MD_LINK.search(model_cell)
        if not m:
            continue
        before_dot = model_cell.split("·")[0]
        provider = before_dot[before_dot.rfind(")") + 1 :].strip() if ")" in before_dot else ""
        score_m = re.search(r"\d+", cells[3])
        if not provider or not score_m:
            continue
        out.append({
            "rank": int(cells[0]),
            "model": m.group(1).strip(),
            "provider": provider,
            "score": int(score_m.group()),
            "votes": cells[4],
        })
    return out


def arena_image_rows(parsed: list[dict[str, Any]], limit: int = 40) -> list[list[Any]]:
    """Map parsed arena.ai rows onto the ``arena_image`` template column order."""
    ranked = sorted(parsed, key=lambda r: r["score"], reverse=True)
    return [
        [i, r["model"], r["provider"], r["score"], r["votes"]]
        for i, r in enumerate(ranked[:limit], start=1)
    ]


def _num(cell: str, cast):
    cell = cell.strip()
    if cell in ("", "--", "—"):
        return "—"
    try:
        return cast(cell)
    except ValueError:
        return cell


def aa_rows(parsed: list[dict[str, Any]], limit: int = 20) -> list[list[Any]]:
    """Map parsed AA rows onto the ``aa`` template column order."""
    rows: list[list[Any]] = []
    for i, r in enumerate(parsed[:limit], start=1):
        price = r["price"].strip()
        price = "—" if price in ("", "--") else price
        rows.append([
            i, r["model"], r["provider"], r["intelligence"],
            _num(r["speed"], int), _num(r["latency"], float),
            r["context"].strip() or "—", price,
        ])
    return rows


# ── JS object-literal editing (string-level, brace/bracket aware) ────────────
def _match_bracket(text: str, open_idx: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    in_str = False
    quote = ""
    esc = False
    for i in range(open_idx, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
        elif ch in "\"'`":
            in_str = True
            quote = ch
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i
    raise ValueError("unbalanced bracket")


def _key_span(block: str, key: str) -> tuple[int, int]:
    m = re.search(r"(?:^|[{,\s])" + re.escape(key) + r"\s*:\s*\{", block)
    if not m:
        raise KeyError(key)
    start = block.index("{", m.start())
    return start, _match_bracket(block, start, "{", "}")


def render_rows_js(rows: list[list[Any]], indent: str = "      ") -> str:
    body = (",\n" + indent).join(json.dumps(r, ensure_ascii=False) for r in rows)
    return "[\n" + indent + body + ",\n    ]"


def replace_field_array(block: str, key: str, field: str, new_array_js: str) -> str:
    try:
        k_start, k_end = _key_span(block, key)
    except KeyError:
        return block
    seg = block[k_start : k_end + 1]
    fm = re.search(re.escape(field) + r"\s*:\s*\[", seg)
    if not fm:
        return block
    arr_open = k_start + seg.index("[", fm.start())
    arr_close = _match_bracket(block, arr_open, "[", "]")
    return block[:arr_open] + new_array_js + block[arr_close + 1 :]


def set_field_string(block: str, key: str, field: str, value: str) -> str:
    try:
        k_start, k_end = _key_span(block, key)
    except KeyError:
        return block
    seg = block[k_start : k_end + 1]
    new_seg = re.sub(re.escape(field) + r'(\s*:\s*")[^"]*(")', rf"{field}\g<1>{value}\g<2>", seg, count=1)
    return block[:k_start] + new_seg + block[k_end + 1 :]


def _overwrite_tab(block: str, key: str, rows: list[list[Any]], updated_label: str | None) -> str:
    if not rows:
        return block
    block = replace_field_array(block, key, "rows", render_rows_js(rows))
    if updated_label:
        block = set_field_string(block, key, "updated", updated_label)
    return block


def apply_crawl_leaderboards(
    block: str, crawl_dir: Path, updated_label: str | None = None, limit: int = 20, image_limit: int = 40
) -> str:
    """Overwrite each crawl-driven tab's rows from its markdown when available."""
    crawl_dir = Path(crawl_dir)

    aa_path = crawl_dir / AA_CRAWL_SLUG
    if aa_path.exists():
        rows = aa_rows(parse_aa_models_md(aa_path.read_text(encoding="utf-8")), limit=limit)
        block = _overwrite_tab(block, "aa", rows, updated_label)

    img_path = crawl_dir / ARENA_T2I_CRAWL_SLUG
    if img_path.exists():
        rows = arena_image_rows(parse_arena_image_md(img_path.read_text(encoding="utf-8")), limit=image_limit)
        block = _overwrite_tab(block, "arena_image", rows, updated_label)

    return block
