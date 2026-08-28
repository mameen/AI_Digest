"""
Add a new top-level digest category to all template files atomically.

Updates (in order):
  1. template.json      — inserts a placeholder category at --after position
  2. template.html      — adds color to CAT_COLORS
  3. SKILL.md           — adds row to Reference table + Categories-to-fill table
  4. _story_utils.py    — adds entry to CATEGORY_META

Optionally also patches an existing digest's JSON + HTML:
  5. PREFIX.json        — inserts an empty category at --after position
  6. PREFIX.html        — rebuilt via rebuild_html.py logic (timestamp updated)

Usage:
    python skills/ai-news-digest/scripts/add_category.py \\
        --id agentic-ai \\
        --label "Agentic AI" \\
        --icon 🤝 \\
        --color "#0EA5E9" \\
        --after aisearch \\
        --search "agentic AI [date]" "MCP Model Context Protocol [date]"

    # Also patch an existing digest:
    python skills/ai-news-digest/scripts/add_category.py ... --prefix 20260515120000

    # Patch latest digest:
    python skills/ai-news-digest/scripts/add_category.py ... --prefix latest
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS_DIR   = Path(__file__).parent
SKILL_DIR     = SCRIPTS_DIR.parent
PROJECT_DIR   = SKILL_DIR.parent.parent
REPORTS_DIR   = PROJECT_DIR / ".reports"
TEMPLATE_JSON = SKILL_DIR / "template.json"
TEMPLATE_HTML = SKILL_DIR / "template.html"
SKILL_MD      = SKILL_DIR / "SKILL.md"
STORY_UTILS   = SCRIPTS_DIR / "_story_utils.py"


# ── Helpers ────────────────────────────────────────────────────────────────────

def die(msg: str) -> None:
    print(f"\n✗  {msg}", file=sys.stderr)
    sys.exit(1)


def latest_prefix() -> str:
    prefixes = sorted(
        p.stem for p in REPORTS_DIR.glob("*.json")
        if len(p.stem) == 14 and p.stem.isdigit()
    )
    if not prefixes:
        die(f"No digest JSON files found in {REPORTS_DIR}")
    return prefixes[-1]


def insert_after_category(categories: list, after_id: str, new_cat: dict) -> None:
    """Insert new_cat immediately after the category with id == after_id."""
    for i, cat in enumerate(categories):
        if cat["id"] == after_id:
            categories.insert(i + 1, new_cat)
            return
    # Fallback: append
    categories.append(new_cat)
    print(f"  ⚠  --after '{after_id}' not found; appended at end", file=sys.stderr)


# ── 1. template.json ──────────────────────────────────────────────────────────

def update_template_json(cat_id: str, label: str, icon: str, after: str) -> None:
    data = json.loads(TEMPLATE_JSON.read_text(encoding="utf-8"))
    cats = data["categories"]

    # Skip if already present
    if any(c["id"] == cat_id for c in cats):
        print(f"  template.json: '{cat_id}' already present — skipped")
        return

    new_cat = {
        "id": cat_id,
        "label": label,
        "icon": icon,
        "stories": [
            {
                "id": f"{cat_id}-example",
                "title": f"Example {label} story",
                "summary": f"Placeholder — replace with real {label} stories each run.",
                "source": "Example Source",
                "url": "https://example.com",
                "significance": 3,
                "novelty": 3,
                "relevance_design": 3,
                "tags": [cat_id],
                "image_url": None,
            }
        ],
    }
    insert_after_category(cats, after, new_cat)

    # Also update category_counts placeholder
    counts = data.setdefault("visualizations", {}).setdefault("category_counts", {})
    if cat_id not in counts:
        counts[cat_id] = 0

    TEMPLATE_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ template.json — added '{cat_id}' after '{after}'")


# ── 2. template.html (CAT_COLORS) ─────────────────────────────────────────────

def update_template_html(cat_id: str, color: str, after: str) -> None:
    text = TEMPLATE_HTML.read_text(encoding="utf-8")

    if f"'{cat_id}'" in text or f'"{cat_id}"' in text and "CAT_COLORS" in text:
        # More precise check
        if re.search(rf"['\"]?{re.escape(cat_id)}['\"]?\s*:", text):
            print(f"  template.html: '{cat_id}' already in CAT_COLORS — skipped")
            return

    # Find CAT_COLORS block and insert after 'after' key
    # Pattern: find the after_id entry and insert after it
    key = f"'{after}'" if after not in ("leaderboard", "llm") else after
    # Try both quoted and unquoted forms for after_id
    patterns = [
        (rf"({re.escape(after)}\s*:\s*'[^']*')", rf"\1, '{cat_id}': '{color}'"),
        (rf"('{re.escape(after)}'\s*:\s*'[^']*')", rf"\1, '{cat_id}': '{color}'"),
    ]
    updated = text
    for pat, repl in patterns:
        new_text = re.sub(pat, repl, updated, count=1)
        if new_text != updated:
            updated = new_text
            break
    else:
        # Fallback: add before the closing brace of CAT_COLORS
        updated = re.sub(
            r"(const CAT_COLORS\s*=\s*\{[^}]+)\}",
            rf"\1, '{cat_id}': '{color}'}}",
            updated,
            count=1,
        )

    TEMPLATE_HTML.write_text(updated, encoding="utf-8")
    print(f"  ✓ template.html — added '{cat_id}': '{color}' to CAT_COLORS")


# ── 3. SKILL.md ───────────────────────────────────────────────────────────────

def update_skill_md(cat_id: str, label: str, icon: str, searches: list[str]) -> None:
    text = SKILL_MD.read_text(encoding="utf-8")

    # Reference table — add row after aisearch row (or after the last | row)
    ref_marker  = "| `aisearch` |"
    new_ref_row = f"| `{cat_id}` | {label} | {icon} | Yes |\n"
    if cat_id not in text:
        text = text.replace(ref_marker, ref_marker + "\n" + new_ref_row, 1)
        print(f"  ✓ SKILL.md — added '{cat_id}' to Reference table")
    else:
        print(f"  SKILL.md Reference table: '{cat_id}' already present — skipped")

    # Categories-to-fill table
    fill_marker  = "| LLMs & Reasoning |"
    search_str   = " OR ".join(f"`{s}`" for s in searches) if searches else f"`{label.lower()} [date]`"
    new_fill_row = f"| {label} | {search_str} |\n"
    if f"| {label} |" not in text:
        text = text.replace(fill_marker, new_fill_row + fill_marker, 1)
        print(f"  ✓ SKILL.md — added '{label}' to Categories-to-fill table")
    else:
        print(f"  SKILL.md Categories-to-fill: '{label}' already present — skipped")

    SKILL_MD.write_text(text, encoding="utf-8")


# ── 4. _story_utils.py (CATEGORY_META) ────────────────────────────────────────

def update_story_utils(cat_id: str, label: str, icon: str) -> None:
    text = STORY_UTILS.read_text(encoding="utf-8")
    if f'"{cat_id}"' in text:
        print(f"  _story_utils.py: '{cat_id}' already in CATEGORY_META — skipped")
        return

    new_entry = f'    "{cat_id}":{" " * max(1, 14 - len(cat_id))}{{"label": "{label}", "icon": "{icon}"}},\n'
    # Insert before the closing brace of CATEGORY_META
    text = text.replace(
        '    "leaderboard":',
        new_entry + '    "leaderboard":',
    )
    STORY_UTILS.write_text(text, encoding="utf-8")
    print(f"  ✓ _story_utils.py — added '{cat_id}' to CATEGORY_META")


# ── 5+6. Patch an existing digest JSON + HTML ─────────────────────────────────

def patch_digest(prefix: str, cat_id: str, label: str, icon: str, after: str) -> None:
    json_path = REPORTS_DIR / f"{prefix}.json"
    html_path = REPORTS_DIR / f"{prefix}.html"

    if not json_path.exists():
        die(f"Digest JSON not found: {json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    cats = data["categories"]

    if any(c["id"] == cat_id for c in cats):
        print(f"  {prefix}.json: '{cat_id}' already present — skipped")
    else:
        new_cat = {"id": cat_id, "label": label, "icon": icon, "stories": []}
        insert_after_category(cats, after, new_cat)
        data["visualizations"]["category_counts"][cat_id] = 0
        data["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  ✓ {prefix}.json — added empty '{cat_id}' category, generated_at updated")

    # Rebuild HTML using rebuild_html logic
    if html_path.exists():
        _rebuild_html(prefix, data)
    else:
        print(f"  ⚠  {prefix}.html not found — skipping HTML rebuild")


def _rebuild_html(prefix: str, data: dict) -> None:
    """Inline rebuild: template CSS+JS + updated digestData + preserved middle."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("rebuild_html", SCRIPTS_DIR / "rebuild_html.py")
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    template_lines = TEMPLATE_HTML.read_text(encoding="utf-8").splitlines(keepends=True)
    html_path      = REPORTS_DIR / f"{prefix}.html"
    existing_lines = html_path.read_text(encoding="utf-8").splitlines(keepends=True)
    middle         = mod.extract_middle(existing_lines)
    html           = mod.build_html(template_lines, data, middle)

    html_path.write_text(html, encoding="utf-8")
    print(f"  ✓ {prefix}.html rebuilt ({len(html):,} bytes)")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="Add a new category to all digest template files")
    p.add_argument("--id",     required=True, help="Category ID (e.g. 'agentic-ai')")
    p.add_argument("--label",  required=True, help="Display label (e.g. 'Agentic AI')")
    p.add_argument("--icon",   required=True, help="Emoji icon (e.g. 🤝)")
    p.add_argument("--color",  required=True, help="Hex color for CAT_COLORS (e.g. '#0EA5E9')")
    p.add_argument("--after",  default="aisearch",
                   help="Insert after this category ID (default: aisearch)")
    p.add_argument("--search", nargs="+", metavar="QUERY",
                   help="Search queries for SKILL.md Categories-to-fill table")
    p.add_argument("--prefix", metavar="PREFIX",
                   help="Also patch this digest (14-digit prefix, or 'latest')")
    args = p.parse_args()

    cat_id  = args.id
    label   = args.label
    icon    = args.icon
    color   = args.color
    after   = args.after
    searches = args.search or []

    print(f"\nAdding category: {icon} {label} (id={cat_id}, color={color}, after={after})")
    print("─" * 60)

    update_template_json(cat_id, label, icon, after)
    update_template_html(cat_id, color, after)
    update_skill_md(cat_id, label, icon, searches)
    update_story_utils(cat_id, label, icon)

    if args.prefix:
        prefix = latest_prefix() if args.prefix == "latest" else args.prefix
        print(f"\nPatching digest {prefix}:")
        patch_digest(prefix, cat_id, label, icon, after)

    print("\n✅  Done.")
    if args.prefix:
        print(f"   Run: python skills/ai-news-digest/scripts/rebuild_html.py {args.prefix if args.prefix != 'latest' else latest_prefix()} --upload")


if __name__ == "__main__":
    main()
