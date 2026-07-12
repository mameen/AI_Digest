"""Recency carry-forward: seed still-empty required categories from prior digests.

No mocks. One test drives the real production helper against a real committed
report JSON (already-published, already-grounded stories); the rest use small
realistic digest-shaped dicts to pin ordering, bounding, and edge behaviour.
"""

from __future__ import annotations

import json
import unittest

from lib.paths import LLM_PIPELINE_ROOT
from llm_pipeline.editorial import make_category
from llm_pipeline.enrich import _carry_forward_empty, _prior_category_stories, _with_provenance

_REPORTS = LLM_PIPELINE_ROOT / "reports"


def _real_report() -> dict:
    for path in sorted(_REPORTS.glob("*.json")):
        if path.name == "index.json":
            continue
        return json.loads(path.read_text(encoding="utf-8"))
    raise unittest.SkipTest("no committed report JSON available")


def _story(sid: str, url: str | None = "https://example.org/x") -> dict:
    return {
        "id": sid, "title": sid.title(), "summary": "s", "source": "Src",
        "url": url, "significance": 3, "novelty": 3, "relevance_design": 3, "tags": [],
    }


def _digest(prefix: str, cats: dict[str, list[dict]]) -> dict:
    return {
        "filename_prefix": prefix,
        "categories": [make_category(cid, stories) for cid, stories in cats.items()],
    }


class PriorCategoryStories(unittest.TestCase):
    def test_returns_only_url_bearing_stories(self) -> None:
        digest = _digest("20260101120000", {
            "rag": [_story("a"), _story("b", url=None), _story("c")],
        })
        got = _prior_category_stories(digest, "rag")
        self.assertEqual([s["id"] for s in got], ["a", "c"])

    def test_absent_category_is_empty(self) -> None:
        self.assertEqual(_prior_category_stories(_digest("x", {}), "rag"), [])


class CarryForward(unittest.TestCase):
    def test_seeds_empty_required_from_most_recent(self) -> None:
        older = _digest("20260101120000", {"rag": [_story("old-1")]})
        newer = _digest("20260102120000", {"rag": [_story("new-1"), _story("new-2")]})
        enriched = {"llm": make_category("llm", [_story("keep")])}
        carried = _carry_forward_empty(
            enriched, [older, newer], ["llm", "rag"], {"rag": 5, "llm": 5}
        )
        self.assertEqual(carried, [("rag", "20260102120000", 2)])  # newest wins
        self.assertEqual([s["id"] for s in enriched["rag"]["stories"]], ["new-1", "new-2"])
        self.assertTrue(all(s["carried_forward"] for s in enriched["rag"]["stories"]))
        self.assertTrue(
            all(s["provenance"] == "carry:20260102120000" for s in enriched["rag"]["stories"])
        )

    def test_non_empty_category_is_untouched(self) -> None:
        enriched = {"rag": make_category("rag", [_story("live")])}
        carried = _carry_forward_empty(
            enriched, [_digest("20260102120000", {"rag": [_story("prior")]})],
            ["rag"], {"rag": 5},
        )
        self.assertEqual(carried, [])
        self.assertEqual([s["id"] for s in enriched["rag"]["stories"]], ["live"])
        self.assertNotIn("carried_forward", enriched["rag"]["stories"][0])

    def test_bounded_to_target(self) -> None:
        prior = _digest("20260102120000", {"rag": [_story(f"s{i}") for i in range(10)]})
        enriched: dict = {}
        _carry_forward_empty(enriched, [prior], ["rag"], {"rag": 3})
        self.assertEqual(len(enriched["rag"]["stories"]), 3)

    def test_no_prior_digests_is_noop(self) -> None:
        enriched: dict = {}
        self.assertEqual(_carry_forward_empty(enriched, [], ["rag"], {"rag": 5}), [])
        self.assertEqual(enriched, {})

    def test_category_absent_everywhere_stays_empty(self) -> None:
        prior = _digest("20260102120000", {"llm": [_story("x")]})
        enriched: dict = {}
        carried = _carry_forward_empty(enriched, [prior], ["rag"], {"rag": 5})
        self.assertEqual(carried, [])
        self.assertNotIn("rag", enriched)

    def test_real_report_seeds_a_real_category(self) -> None:
        report = _real_report()
        target_cid = next(
            (c["id"] for c in report.get("categories") or []
             if any(s.get("url") for s in c.get("stories") or [])),
            None,
        )
        self.assertIsNotNone(target_cid, "report should have a url-bearing category")
        enriched: dict = {}
        carried = _carry_forward_empty(enriched, [report], [target_cid], {target_cid: 5})
        self.assertEqual(len(carried), 1)
        seeded = enriched[target_cid]["stories"]
        self.assertTrue(seeded and all(s.get("url") for s in seeded))
        self.assertTrue(all(s["carried_forward"] for s in seeded))


class WithProvenance(unittest.TestCase):
    """Provenance stamping: trace each story back to the stage that produced it."""

    def test_stamps_missing_tokens(self) -> None:
        stories = [_story("a"), _story("b")]
        out = _with_provenance(stories, "gap:rag")
        self.assertIs(out, stories)  # mutates + returns the same list
        self.assertTrue(all(s["provenance"] == "gap:rag" for s in stories))

    def test_preserves_existing_tokens(self) -> None:
        stories = [dict(_story("a"), provenance="carry:20260101120000"), _story("b")]
        _with_provenance(stories, "gap:rag")
        self.assertEqual(stories[0]["provenance"], "carry:20260101120000")  # untouched
        self.assertEqual(stories[1]["provenance"], "gap:rag")  # filled

    def test_ignores_non_dict_entries(self) -> None:
        stories = [_story("a"), "not-a-dict"]  # type: ignore[list-item]
        _with_provenance(stories, "gap:rag")
        self.assertEqual(stories[0]["provenance"], "gap:rag")


if __name__ == "__main__":
    unittest.main()
