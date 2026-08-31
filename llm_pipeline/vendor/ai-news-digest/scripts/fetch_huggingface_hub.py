"""Bounded discovery across the Hugging Face Models, Datasets, and Spaces hubs."""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _story_utils import make_category, make_story

API_ROOT = "https://huggingface.co/api"
QUERIES = ("text to speech", "audio", "multimodal", "agent", "computer vision")
ENDPOINTS = {"models": "Models", "datasets": "Datasets", "spaces": "Spaces"}
PER_QUERY = 3
TOTAL_LIMIT = 15


def _fetch(kind: str, query: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "search": query,
        "sort": "lastModified",
        "direction": "-1",
        "limit": str(PER_QUERY),
        "full": "true",
    })
    request = urllib.request.Request(
        f"{API_ROOT}/{kind}?{params}",
        headers={"User-Agent": "Orio-AI-News-Digest"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def discover() -> list[dict]:
    seen: set[tuple[str, str]] = set()
    items: list[dict] = []
    for kind, label in ENDPOINTS.items():
        for query in QUERIES:
            try:
                rows = _fetch(kind, query)
            except Exception as exc:
                print(f"  Hugging Face {label} ({query}): {exc}", file=sys.stderr)
                continue
            for row in rows:
                item_id = row.get("id") or row.get("name")
                if not item_id or (kind, item_id) in seen:
                    continue
                seen.add((kind, item_id))
                items.append({
                    "kind": kind,
                    "label": label,
                    "id": item_id,
                    "url": f"https://huggingface.co/{kind}/{item_id}",
                    "downloads": row.get("downloads", 0),
                    "likes": row.get("likes", 0),
                    "lastModified": row.get("lastModified", ""),
                })
                if len(items) >= TOTAL_LIMIT:
                    return items
    return items


def to_story_cards(items: list[dict]) -> list[dict]:
    stories = []
    for item in items:
        title = f"{item['label']}: {item['id']}"
        snippet = f"Hugging Face {item['label']}; {item['downloads']:,} downloads; {item['likes']} likes"
        stories.append(make_story(
            title, item["url"], f"Hugging Face {item['label']}",
            raw_snippet=snippet,
            extra_tags=["hugging-face", f"hf-{item['kind']}"],
        ))
    return stories


def fetch_stories() -> dict:
    return make_category("research", to_story_cards(discover()))


if __name__ == "__main__":
    print(json.dumps(fetch_stories(), indent=2, ensure_ascii=False))
