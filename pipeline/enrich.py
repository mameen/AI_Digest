"""Stage 3: multi-pass LLM enrich via Instructor (production SKILL style)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.dates import RunWindow
from pipeline.editorial import (
    CANONICAL_ORDER,
    GAP_CATEGORY_IDS,
    SKELETON_CATEGORY_IDS,
    build_ingestion_context,
    category_targets,
    enrich_cfg,
    extract_aisearch_meta,
    load_editorial_brief,
    make_category,
    normalize_preflight_category,
    order_categories,
    skeleton_category_map,
    stories_for_prompt,
    strip_private_fields,
)
from pipeline.grounding import collect_roots, strip_ungrounded
from pipeline.history import format_prior_context
from pipeline.diagnostics import instrumented_llm_call
from pipeline.schema import CategoryStories, DigestHeader, GapCategories
from pipeline.visualize import compute_visualizations, fill_skeleton_stories


def enrich_digest(
    cfg: dict[str, Any],
    window: RunWindow,
    preflight_path: Path,
    crawl_md: list[Path],
    prior_digests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Merge preflight skeleton + crawled markdown into a full digest JSON.

    When llm.enabled is false, promote preflight categories as-is (unscored skeleton).
    When enabled, run multi-pass local LLM enrichment (no vector RAG).
    """
    llm_cfg = cfg.get("llm", {})
    skeleton = json.loads(preflight_path.read_text(encoding="utf-8"))
    prior = prior_digests or []

    if not llm_cfg.get("enabled"):
        print("  llm.enabled=false: promoting preflight skeleton (no LLM enrich)")
        return _promote_skeleton(window, skeleton)

    library = llm_cfg.get("structured_output", {}).get("library", "instructor")
    if library != "instructor":
        raise SystemExit(
            f"structured_output.library={library!r} not implemented yet. "
            "Use instructor or set llm.enabled=false."
        )

    return _enrich_multipass(cfg, window, skeleton, crawl_md, prior)


def _promote_skeleton(window: RunWindow, skeleton: dict[str, Any]) -> dict[str, Any]:
    categories = [
        normalize_preflight_category(c) for c in fill_skeleton_stories(skeleton.get("categories") or [])
    ]
    video_url, video_label = extract_aisearch_meta(skeleton.get("categories") or [])
    out = {
        "generated_at": window.generated_at,
        "filename_prefix": window.prefix,
        "summary": skeleton.get("summary")
        or f"Skeleton digest for {window.label()}. Run with llm.enabled for full enrich.",
        "categories": order_categories([strip_private_fields(c) for c in categories]),
        "aisearch_video_url": video_url,
        "aisearch_video_label": video_label,
        "visualizations": compute_visualizations(categories),
    }
    return out


def _enrich_multipass(
    cfg: dict[str, Any],
    window: RunWindow,
    skeleton: dict[str, Any],
    crawl_md: list[Path],
    prior_digests: list[dict[str, Any]],
) -> dict[str, Any]:
    from pipeline.llm_client import make_client

    client, model, max_retries = make_client(cfg)
    ecfg = enrich_cfg(cfg)
    batch_size = int(ecfg.get("stories_per_batch", 18))
    targets = category_targets(cfg)

    brief = load_editorial_brief()
    ingestion = build_ingestion_context(skeleton, crawl_md)
    prior_context = format_prior_context(prior_digests)
    skel_map = skeleton_category_map(skeleton)
    enriched: dict[str, dict[str, Any]] = {}

    # ── Pass 1: score + summarize preflight categories ───────────────────────
    for cat_id in CANONICAL_ORDER:
        if cat_id not in SKELETON_CATEGORY_IDS or cat_id not in skel_map:
            continue
        raw_cat = skel_map[cat_id]
        stories = raw_cat.get("stories") or []
        if not stories:
            continue
        print(f"  [enrich] {cat_id} ({len(stories)} stories)")
        merged: list[dict[str, Any]] = []
        for i in range(0, len(stories), batch_size):
            batch = stories[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(stories) + batch_size - 1) // batch_size
            label = f"batch {batch_num}/{total_batches}" if total_batches > 1 else "all"
            result = _llm_category_enrich(
                client,
                model,
                max_retries,
                brief=brief,
                window=window,
                cat_id=cat_id,
                cat_label=raw_cat.get("label", cat_id),
                stories_json=stories_for_prompt(batch),
                extra_rules=_skeleton_rules(cat_id, curate_after=targets.get(cat_id) is not None),
                ingestion=ingestion if cat_id == "research" else "",
                prior_context=prior_context if i == 0 else "",
                batch_label=label,
                call_name=f"enrich.{cat_id}.{label.replace(' ', '_')}",
            )
            merged.extend([s.model_dump() for s in result.stories])
        curated = _apply_target_count(
            client, model, max_retries, cat_id, raw_cat.get("label", cat_id), merged, targets.get(cat_id), brief
        )
        enriched[cat_id] = make_category(cat_id, curated)

    # ── Pass 2: leaderboard from crawled pages ─────────────────────────────
    lb_target = targets.get("leaderboard") or 6
    print(f"  [enrich] leaderboard (from crawls, target={lb_target})")
    lb = _llm_leaderboard(
        client,
        model,
        max_retries,
        brief=brief,
        window=window,
        ingestion=ingestion,
        prior_context=prior_context,
        story_count=lb_target,
    )
    enriched["leaderboard"] = make_category("leaderboard", [s.model_dump() for s in lb.stories])

    # ── Pass 3: gap categories (analytics, agentic, llm, rag, image, design, robotics) ─
    gap_ids = [c for c in CANONICAL_ORDER if c in GAP_CATEGORY_IDS]
    chunk_size = int(ecfg.get("gap_categories_per_call", 3))
    gap_chunks = [gap_ids[i : i + chunk_size] for i in range(0, len(gap_ids), chunk_size)]
    for chunk in gap_chunks:
        if not chunk:
            continue
        print(f"  [enrich] gap fill: {', '.join(chunk)}")
        per_cat = {cid: targets.get(cid) or 5 for cid in chunk}
        gap = _llm_gap_fill(
            client,
            model,
            max_retries,
            brief=brief,
            window=window,
            category_ids=chunk,
            ingestion=ingestion,
            prior_context=prior_context,
            enriched_so_far=_categories_summary(enriched),
            stories_per_category=per_cat,
        )
        for cat in gap.categories:
            enriched[cat.id] = make_category(cat.id, [s.model_dump() for s in cat.stories])

    # ── Guard: drop stories that cite a bare leaderboard/crawl root ───────────
    roots = collect_roots(skeleton.get("requires_web_fetch"))
    cleaned, dropped = strip_ungrounded(list(enriched.values()), roots)
    if dropped:
        print(f"  [guard] dropped {len(dropped)} ungrounded stories (no real article url)")
        for d in dropped:
            print(f"          - {d['category']}: {d['source']!r} -> {d['url']}")
    enriched = {c["id"]: c for c in cleaned}

    # ── Pass 4: daily summary + video metadata ───────────────────────────────
    categories = order_categories(list(enriched.values()))
    video_url, video_label = extract_aisearch_meta(skeleton.get("categories") or [])
    print("  [enrich] daily summary")
    header = _llm_summary(
        client,
        model,
        max_retries,
        brief=brief,
        window=window,
        categories_summary=_categories_summary(enriched),
        default_video_url=video_url,
        default_video_label=video_label,
    )

    out = {
        "generated_at": window.generated_at,
        "filename_prefix": window.prefix,
        "summary": header.summary,
        "aisearch_video_url": header.aisearch_video_url or video_url,
        "aisearch_video_label": header.aisearch_video_label or video_label,
        "categories": categories,
        "visualizations": compute_visualizations(categories),
    }
    _log_category_counts(categories)
    return out


def _log_category_counts(categories: list[dict[str, Any]]) -> None:
    parts = [f"{c.get('id')}={len(c.get('stories') or [])}" for c in categories]
    total = sum(len(c.get("stories") or []) for c in categories)
    print(f"  [counts] total={total}  {'  '.join(parts)}")


def _skeleton_rules(cat_id: str, *, curate_after: bool = False) -> str:
    if cat_id == "aisearch":
        if curate_after:
            return (
                "Enrich every chapter in this batch (same ids and urls). "
                "Score significance from how much attention the video gives the topic."
            )
        return (
            "CRITICAL: return exactly the same number of stories as input. "
            "Keep every chapter (same ids and urls). Only enrich summary, scores, tags, title polish."
        )
    if cat_id == "research":
        return "Score papers by significance to AI practitioners; tag with arxiv/topics."
    if cat_id == "typography":
        return "Prioritize text rendering, multilingual fonts, and design workflow impact."
    return ""


def _apply_target_count(
    client: Any,
    model: str,
    max_retries: int,
    cat_id: str,
    cat_label: str,
    stories: list[dict[str, Any]],
    target: int | None,
    brief: str,
) -> list[dict[str, Any]]:
    """Trim skeleton categories to production-style counts (incl. aisearch when target set)."""
    if target is None or len(stories) <= target:
        return stories
    print(f"  [curate] {cat_id}: {len(stories)} -> {target}")
    if len(stories) <= target * 2:
        ranked = sorted(
            stories,
            key=lambda s: (
                -int(s.get("significance") or 0),
                -int(s.get("novelty") or 0),
                -int(s.get("relevance_design") or 0),
            ),
        )
        return ranked[:target]
    result = _llm_curate_category(
        client, model, max_retries, cat_id, cat_label, stories, target, brief
    )
    return [s.model_dump() for s in result.stories]


def _llm_curate_category(
    client: Any,
    model: str,
    max_retries: int,
    cat_id: str,
    cat_label: str,
    stories: list[dict[str, Any]],
    target: int,
    brief: str,
) -> CategoryStories:
    prompt = f"""{brief}

## Task
Curate **{cat_label}** (`{cat_id}`) to exactly **{target}** stories for the daily digest.

From the enriched candidates below, pick the {target} most significant and diverse stories.
Return the full story objects unchanged (same id, url, source). Only drop lower-priority entries.
{f"For aisearch: prefer chapters theAIsearch spent the most time on; keep exact YouTube chapter urls." if cat_id == "aisearch" else ""}

## Candidates ({len(stories)} stories)
{stories_for_prompt(stories)}

Return JSON with exactly {target} stories."""
    return _llm_call(
        client, model, max_retries, prompt, CategoryStories, call_name=f"curate.{cat_id}"
    )


def _categories_summary(enriched: dict[str, dict[str, Any]]) -> str:
    lines: list[str] = []
    for cid in CANONICAL_ORDER:
        cat = enriched.get(cid)
        if not cat:
            continue
        stories = cat.get("stories") or []
        titles = [s.get("title", "") for s in stories[:5]]
        lines.append(f"- {cid}: {len(stories)} stories, e.g. {titles[0]!r}" if titles else f"- {cid}: 0")
    return "\n".join(lines)


def _llm_call(
    client: Any,
    model: str,
    max_retries: int,
    prompt: str,
    response_model: type,
    *,
    call_name: str = "llm",
) -> Any:
    return instrumented_llm_call(
        client,
        model,
        max_retries,
        prompt,
        response_model,
        call_name=call_name,
    )


def _llm_category_enrich(
    client: Any,
    model: str,
    max_retries: int,
    *,
    brief: str,
    window: RunWindow,
    cat_id: str,
    cat_label: str,
    stories_json: str,
    extra_rules: str,
    ingestion: str,
    prior_context: str,
    batch_label: str,
    call_name: str,
) -> CategoryStories:
    prompt = f"""{brief}

## Task
Enrich category **{cat_label}** (`{cat_id}`), {batch_label}.
Editorial window: {window.history_from.isoformat()} through {window.start.isoformat()}.

## Input stories (keep ids and urls exactly)
{stories_json}

{f"## Extra rules{chr(10)}{extra_rules}" if extra_rules else ""}
{f"## Ingestion context{chr(10)}{ingestion[:8000]}" if ingestion else ""}
{f"## Prior digests{chr(10)}{prior_context}" if prior_context else ""}

Return JSON with enriched stories only."""
    return _llm_call(client, model, max_retries, prompt, CategoryStories, call_name=call_name)


def _llm_leaderboard(
    client: Any,
    model: str,
    max_retries: int,
    *,
    brief: str,
    window: RunWindow,
    ingestion: str,
    prior_context: str,
    story_count: int = 6,
) -> CategoryStories:
    prompt = f"""{brief}

## Task
Author the **Leaderboard Rankings** category with exactly **{story_count}** stories.
Editorial window: {window.history_from.isoformat()} through {window.start.isoformat()}.

Use crawled leaderboard markdown and llm-stats below. Include:
- Current #1 closed model + notable rank changes
- Open-weight leader + open vs closed gap
- Image arena / text-rendering leaders when data supports it

## Ingestion context
{ingestion[:24000]}

## Prior digests
{prior_context}

Story ids should start with `lb-`. Return JSON with exactly {story_count} stories."""
    return _llm_call(
        client, model, max_retries, prompt, CategoryStories, call_name="enrich.leaderboard"
    )


def _llm_gap_fill(
    client: Any,
    model: str,
    max_retries: int,
    *,
    brief: str,
    window: RunWindow,
    category_ids: list[str],
    ingestion: str,
    prior_context: str,
    enriched_so_far: str,
    stories_per_category: dict[str, int],
) -> GapCategories:
    cats = ", ".join(category_ids)
    counts = ", ".join(f"{cid}={stories_per_category[cid]}" for cid in category_ids)
    prompt = f"""{brief}

## Task
Author editorial stories for categories: **{cats}**.
Editorial window: {window.history_from.isoformat()} through {window.start.isoformat()}.
Target counts: {counts}.

## Source grounding (STRICT)
- Every story MUST cite a real, specific article/page `url` that appears verbatim in the Ingestion context below.
- NEVER invent a `source` name. Use the actual publisher exactly (e.g. "Artificial Analysis", "Arena.ai", "Vellum").
- Leaderboard *index/root* pages (e.g. `.../leaderboards/models`, `.../leaderboard/text-to-image`, `vellum.ai/*-leaderboard`) are NOT article links — never cite them here; those belong to the leaderboard category.
- If you cannot ground a story in a real, specific URL from the context, write FEWER stories (even zero) for that category. Do not fabricate to hit the count.

## Already covered (do not duplicate)
{enriched_so_far}

## Ingestion context
{ingestion[:28000]}

## Prior digests
{prior_context}

Category ids must be exactly: {json.dumps(category_ids)}.
Use placeholder label/icon per category; the pipeline assigns canonical names.
Return JSON with categories array (id, label, icon, stories)."""
    return _llm_call(
        client,
        model,
        max_retries,
        prompt,
        GapCategories,
        call_name=f"enrich.gap.{','.join(category_ids)}",
    )


def _llm_summary(
    client: Any,
    model: str,
    max_retries: int,
    *,
    brief: str,
    window: RunWindow,
    categories_summary: str,
    default_video_url: str | None,
    default_video_label: str | None,
) -> DigestHeader:
    prompt = f"""{brief}

## Task
Write the digest header for prefix {window.prefix}.
One-sentence `summary` capturing the day's biggest themes (production magazine style).

## Categories in this digest
{categories_summary}

Default aisearch video (use unless you have a better label):
url={default_video_url!r}
label={default_video_label!r}

Return JSON: summary, aisearch_video_url, aisearch_video_label."""
    return _llm_call(
        client, model, max_retries, prompt, DigestHeader, call_name="enrich.summary"
    )
