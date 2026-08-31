"""Fetch a bounded, task-focused slice of the Hugging Face model hub."""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from _story_utils import make_category, make_story

API = "https://huggingface.co/api/models"
TASKS = {
    "text-to-speech": "Text-to-speech and voice generation",
    "automatic-speech-recognition": "Automatic speech recognition",
    "audio-to-audio": "Audio transformation and voice conversion",
    "audio-text-to-text": "Audio understanding and speech-language models",
    "text-to-audio": "Text-to-audio generation",
    "voice-conversion": "Voice conversion",
}
PER_TASK = 4
TOTAL_LIMIT = 12


def _fetch_task(task: str, limit: int = PER_TASK) -> list[dict]:
    query = urllib.parse.urlencode({
        "pipeline_tag": task,
        "sort": "lastModified",
        "direction": "-1",
        "limit": str(limit),
        "full": "true",
    })
    url = f"{API}?{query}"
    request = urllib.request.Request(url, headers={"User-Agent": "Orio-AI-News-Digest"})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_models() -> list[dict]:
    seen: set[str] = set()
    models: list[dict] = []
    for task in TASKS:
        try:
            rows = _fetch_task(task)
        except Exception as exc:
            print(f"  Hugging Face {task}: {exc}", file=sys.stderr)
            continue
        for row in rows:
            model_id = row.get("id")
            if not model_id or model_id in seen:
                continue
            seen.add(model_id)
            models.append({
                "id": model_id,
                "url": f"https://huggingface.co/{model_id}",
                "task": task,
                "downloads": row.get("downloads", 0),
                "likes": row.get("likes", 0),
                "lastModified": row.get("lastModified", ""),
            })
            if len(models) >= TOTAL_LIMIT:
                return models
    return models


def to_story_cards(models: list[dict]) -> list[dict]:
    stories = []
    for model in models:
        task_label = TASKS[model["task"]]
        signal = f"{task_label}; {model['downloads']:,} downloads; {model['likes']} likes"
        stories.append(make_story(
            model["id"].replace("/", " / "), model["url"], "Hugging Face Models",
            raw_snippet=signal,
            extra_tags=["hugging-face", "model-hub", "speech", model["task"]],
        ))
    return stories


def fetch_stories() -> dict:
    return make_category("voice-speech", to_story_cards(fetch_models()))


if __name__ == "__main__":
    print(json.dumps(fetch_stories(), indent=2, ensure_ascii=False))
