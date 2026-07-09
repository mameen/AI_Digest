"""Structured JSON API extractor — leaderboard rows from cached endpoint payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm_pipeline.paths import cache_dir
from llm_pipeline.structured_sources import evalplus_rows, swebench_rows

from lib.ingest.fixtures import fixture_path
from lib.ingest.types import IngestBundle, ResearchBullet

SWE_URL = "https://www.swebench.com/"
EVAL_URL = "https://evalplus.github.io/"


def read_structured_json(cfg: dict[str, Any], bundle: IngestBundle, slug: str) -> dict[str, Any] | None:
    structured_dir = cache_dir(cfg) / bundle.prefix / "structured"
    path = structured_dir / slug
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    for row in bundle.structured_paths:
        if row.name == slug and row.is_file():
            return json.loads(row.read_text(encoding="utf-8"))
    fixture = fixture_path(slug)
    if fixture.is_file():
        return json.loads(fixture.read_text(encoding="utf-8"))
    return None


def bullets_from_structured_json(cfg: dict[str, Any], bundle: IngestBundle) -> list[ResearchBullet]:
    bullets: list[ResearchBullet] = []

    swe = read_structured_json(cfg, bundle, "swebench_leaderboards.json")
    if swe:
        for row in swebench_rows(swe, limit=3):
            name = row[1] if len(row) > 1 else "model"
            resolved = row[3] if len(row) > 3 else "—"
            bullets.append(
                ResearchBullet(
                    title=f"SWE-bench Verified: {name} ({resolved}% resolved)",
                    url=SWE_URL,
                )
            )

    eval_data = read_structured_json(cfg, bundle, "evalplus_results.json")
    if eval_data:
        for row in evalplus_rows(eval_data, limit=3):
            name = row[1] if len(row) > 1 else "model"
            he = row[3] if len(row) > 3 else "—"
            bullets.append(
                ResearchBullet(
                    title=f"EvalPlus HumanEval+: {name} (pass@1 {he})",
                    url=EVAL_URL,
                )
            )
    return bullets
