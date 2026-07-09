"""Stage 3b: output validation (concrete gates from OWUI lessons)."""

from __future__ import annotations

from typing import Any


def validate_digest(
    cfg: dict[str, Any], data: dict[str, Any], roots: set[str] | None = None
) -> list[str]:
    from llm_pipeline.grounding import collect_roots, find_ungrounded

    vcfg = cfg.get("validation", {})
    errors: list[str] = []

    categories = data.get("categories") or []
    cat_ids = {c.get("id") for c in categories}
    total = sum(len(c.get("stories") or []) for c in categories)

    min_stories = int(vcfg.get("min_total_stories", 0))
    if total < min_stories:
        errors.append(f"story count {total} < min_total_stories {min_stories}")

    min_cats = int(vcfg.get("min_categories", 0))
    if len(categories) < min_cats:
        errors.append(f"categories {len(categories)} < min_categories {min_cats}")

    for req in vcfg.get("required_category_ids") or []:
        if req not in cat_ids:
            errors.append(f"missing required category: {req}")

    if not data.get("summary"):
        errors.append("missing summary")

    # Skeleton categories must be curated (not raw preflight counts)
    targets = (cfg.get("enrich") or {}).get("category_targets") or {}
    counts = {c.get("id"): len(c.get("stories") or []) for c in categories}
    for cid, limit in (("typography", 6), ("research", 10), ("aisearch", 15)):
        target = targets.get(cid)
        if target is not None and counts.get(cid, 0) > max(int(target), limit):
            errors.append(f"{cid} count {counts[cid]} looks uncured (target {target})")

    # Source grounding: non-leaderboard stories must not cite a bare leaderboard/crawl root
    check_roots = roots if roots is not None else collect_roots(None)
    for off in find_ungrounded(categories, check_roots):
        errors.append(
            f"ungrounded story in {off['category']}: {off['source']!r} -> {off['url']}"
        )

    return errors


def apply_validation(cfg: dict[str, Any], errors: list[str]) -> None:
    if not errors:
        print("  OK validation passed")
        return
    for err in errors:
        print(f"  WARN validation: {err}")
    if cfg.get("validation", {}).get("fail_on_missing"):
        raise SystemExit(f"Validation failed ({len(errors)} issues)")
