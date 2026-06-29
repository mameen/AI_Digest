"""
Shared utilities for converting scraped articles into digest story-card dicts.

Story card schema (matches YYYYMMDDHHMMSS.json → categories[].stories[]):
  {
    "id":               str,   # unique slug, e.g. "typo-monotype-ai-search"
    "title":            str,   # article / paper / chapter title
    "summary":          str,   # "" — Claude fills this in
    "source":           str,   # site name, e.g. "Monotype Newsroom"
    "url":              str,   # canonical URL
    "significance":     int,   # 0 = unscored (Claude fills); 1–5 when scored
    "novelty":          int,   # 0 = unscored
    "relevance_design": int,   # 0 = unscored
    "tags":             list,  # auto-extracted keywords
    "image_url":        None,
    "raw_snippet":      str,   # extra context to help Claude write the summary
  }
"""

import re


# ── Tag extraction ─────────────────────────────────────────────────────────────

_TAG_RULES: list[tuple[str, list[str]]] = [
    ("ai",              ["artificial intelligence", " ai ", "machine learning", "neural", "llm", "gpt", "generative"]),
    ("font",            ["font", "typeface", "typefaces"]),
    ("typography",      ["typography", "typographic", "typographer"]),
    ("variable-fonts",  ["variable font", "opentype"]),
    ("text-rendering",  ["text render", "text-to-image", "text in image"]),
    ("monotype",        ["monotype"]),
    ("adobe",           ["adobe", "firefly", "illustrator", "indesign"]),
    ("diffusion",       ["diffusion", "stable diffusion", "flux"]),
    ("multimodal",      ["multimodal", "vision-language", "vlm"]),
    ("open-source",     ["open source", "open-source", "open-weight", "github", "apache", "mit license"]),
    ("benchmark",       ["benchmark", "leaderboard", "eval", "swe-bench", "gpqa"]),
    ("robotics",        ["robot", "embodied", "humanoid"]),
    ("reasoning",       ["reasoning", "chain-of-thought", "cot", "math"]),
    ("design",          ["design", "figma", "canva", "ui", "ux", "layout"]),
    ("image-gen",       ["image gen", "text-to-image", "image generation", "image model"]),
    ("research",        ["arxiv", "paper", "preprint"]),
    ("codesign",        ["co-design", "codesign", "collaborative design", "co-pilot"]),
]


def extract_tags(text: str) -> list[str]:
    t = text.lower()
    return [tag for tag, keywords in _TAG_RULES if any(kw in t for kw in keywords)]


# ── Slug generation ────────────────────────────────────────────────────────────

def make_slug(title: str, prefix: str = "", max_len: int = 50) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:max_len].rstrip("-")
    return f"{prefix}-{slug}" if prefix else slug


# ── Story card factory ─────────────────────────────────────────────────────────

def make_story(
    title: str,
    url: str,
    source: str,
    *,
    id_prefix: str = "",
    raw_snippet: str = "",
    extra_tags: list[str] | None = None,
) -> dict:
    """Build a story-card dict with auto-extracted tags and empty score fields."""
    slug = make_slug(title, prefix=id_prefix or _prefix_for_source(source))
    tags = extract_tags(title + " " + raw_snippet)
    if extra_tags:
        for t in extra_tags:
            if t not in tags:
                tags.append(t)
    return {
        "id":               slug,
        "title":            title.strip(),
        "summary":          "",
        "source":           source,
        "url":              url,
        "significance":     0,
        "novelty":          0,
        "relevance_design": 0,
        "tags":             tags,
        "image_url":        None,
        "raw_snippet":      raw_snippet.strip(),
    }


def _prefix_for_source(source: str) -> str:
    mapping = {
        "Monotype Newsroom":  "typo",
        "Monotype Resources": "typo",
        "I Love Typography":  "typo",
        "Adobe Fonts Blog":   "typo",
        "Typographica":       "typo",
        "MyFonts Blog":       "typo",
        "HuggingFace Papers": "res",
        "arXiv cs.AI":        "res",
        "arXiv cs.CV":        "res",
        "arXiv cs.CL":        "res",
        "theAIsearch":        "ais",
        "LLM Stats":          "llm",
    }
    return mapping.get(source, "story")


# ── Category envelope ──────────────────────────────────────────────────────────

CATEGORY_META = {
    "aisearch":   {"label": "AI Search",                      "icon": "🔍"},
    "typography": {"label": "Typography & Text Rendering",    "icon": "🔤"},
    "research":   {"label": "Research & Papers",              "icon": "📄"},
    "llm":        {"label": "LLMs & Reasoning",               "icon": "🧠"},
    "image-gen":  {"label": "Image Generation & Processing",  "icon": "🎨"},
    "design-ai":  {"label": "Design & Creative AI",           "icon": "✏️"},
    "robotics":   {"label": "Robotics & Embodied AI",         "icon": "🤖"},
    "leaderboard":{"label": "Leaderboard Rankings",           "icon": "🏆"},
}


def make_category(category_id: str, stories: list[dict]) -> dict:
    meta = CATEGORY_META.get(category_id, {"label": category_id, "icon": "📌"})
    return {
        "id":      category_id,
        "label":   meta["label"],
        "icon":    meta["icon"],
        "stories": stories,
    }
