"""Read raw story stubs from a preflight skeleton category — no topic-specific prose."""

from __future__ import annotations

from typing import Any

from lib.ingest.topics._preflight import category_from_preflight, story_bullets_from_category
from lib.ingest.types import IngestBundle, ResearchBullet


def bullets_from_category(
    preflight: dict[str, Any],
    category_id: str,
    *,
    max_bullets: int = 12,
) -> list[ResearchBullet]:
    cat = category_from_preflight(preflight, category_id)
    if not cat:
        return []
    return story_bullets_from_category(cat, max_bullets=max_bullets)


def bullets_from_bundle_category(bundle: IngestBundle, category_id: str) -> list[ResearchBullet]:
    return bullets_from_category(bundle.preflight, category_id)
