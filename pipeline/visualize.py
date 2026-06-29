"""Compute digest visualizations block (required by digest-app.js)."""

from __future__ import annotations

from collections import Counter
from typing import Any


def compute_visualizations(categories: list[dict[str, Any]]) -> dict[str, Any]:
    """Build category_counts, significance_distribution, top_tags, top_stories."""
    category_counts: dict[str, int] = {}
    sig_dist: Counter[int] = Counter()
    tag_counts: Counter[str] = Counter()
    ranked: list[tuple[int, int, str, str, str]] = []

    for idx, cat in enumerate(categories):
        cat_id = cat.get("id") or f"cat-{idx}"
        stories = cat.get("stories") or []
        category_counts[cat_id] = len(stories)
        for story in stories:
            sig = int(story.get("significance") or 0)
            sig_dist[sig] += 1
            for tag in story.get("tags") or []:
                if tag:
                    tag_counts[str(tag)] += 1
            ranked.append(
                (
                    sig,
                    int(story.get("novelty") or 0),
                    story.get("id") or "",
                    story.get("title") or "",
                    cat_id,
                )
            )

    ranked.sort(key=lambda r: (r[0], r[1], -len(r[3])), reverse=True)
    top_stories = [
        {"id": sid, "title": title, "significance": sig, "category": cat_id}
        for sig, _, sid, title, cat_id in ranked[:5]
        if sid and title
    ]

    # digest-app.js keys significance_distribution as "5".."1"
    significance_distribution = {str(k): v for k, v in sorted(sig_dist.items(), reverse=True)}

    top_tags = [{"tag": tag, "count": count} for tag, count in tag_counts.most_common(10)]

    return {
        "category_counts": category_counts,
        "significance_distribution": significance_distribution,
        "top_tags": top_tags,
        "top_stories": top_stories,
    }


def fill_skeleton_stories(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Fill empty summaries from raw_snippet/title so skeleton cards are readable."""
    out: list[dict[str, Any]] = []
    for cat in categories:
        cat_copy = dict(cat)
        stories: list[dict[str, Any]] = []
        for story in cat.get("stories") or []:
            s = dict(story)
            if not (s.get("summary") or "").strip():
                snippet = (s.get("raw_snippet") or "").strip()
                s["summary"] = snippet or f"{s.get('title', 'Story')}: awaiting LLM enrich."
            stories.append(s)
        cat_copy["stories"] = stories
        out.append(cat_copy)
    return out
