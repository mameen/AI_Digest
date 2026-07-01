"""Tests for the prompt-registered tool-calling loop.

No mocks or monkeypatching of production code: the only I/O seams (the LLM
``chat`` and the URL ``fetch``) are dependency-injected, so the driver runs
against a deterministic scripted transcript and a fixture status map exactly as
it would against the live model + network.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from pipeline.tools import (
    ToolAction,
    format_tool_result,
    parse_ddg_results,
    parse_tool_action,
    run_tool_loop,
    verify_url,
    web_search,
)

_DDG_FIXTURE = Path(__file__).parent / "data" / "duckduckgo_html_results.html"


class ScriptedChat:
    """A deterministic stand-in for the LLM: replays canned replies in order."""

    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.turns: list[list[dict[str, str]]] = []

    def __call__(self, messages: list[dict[str, str]]) -> str:
        self.turns.append([dict(m) for m in messages])
        return self.replies[min(len(self.turns) - 1, len(self.replies) - 1)]


def _fetch_from(status_map: dict[str, int]):
    def fetch(url: str, timeout: int) -> tuple[int | None, str]:
        return status_map.get(url), url

    return fetch


def _serve(html_text: str):
    """A fixture ``fetch_html`` seam: return the same page for any query."""

    def fetch_html(query: str, timeout: int) -> str:
        return html_text

    return fetch_html


class ParseAction(unittest.TestCase):
    def test_plain_action(self) -> None:
        a = parse_tool_action('{"action": "verify_url", "args": {"url": "https://x.io/a"}}')
        self.assertEqual((a.name, a.args["url"]), ("verify_url", "https://x.io/a"))

    def test_action_inside_prose_and_fence(self) -> None:
        text = 'Sure!\n```json\n{"action":"finalize","args":{"result":"{}"}}\n```\nDone.'
        a = parse_tool_action(text)
        self.assertEqual(a.name, "finalize")

    def test_brace_in_string_does_not_break_scan(self) -> None:
        a = parse_tool_action('{"action":"web_search","args":{"query":"a { b } c"}}')
        self.assertEqual(a.args["query"], "a { b } c")

    def test_non_action_returns_none(self) -> None:
        self.assertIsNone(parse_tool_action("no json here"))
        self.assertIsNone(parse_tool_action('{"foo": 1}'))


class VerifyUrl(unittest.TestCase):
    def test_live_url_ok(self) -> None:
        r = verify_url("https://site.io/real", fetch=_fetch_from({"https://site.io/real": 200}))
        self.assertTrue(r["ok"])
        self.assertEqual(r["status"], 200)

    def test_dead_url_not_ok(self) -> None:
        r = verify_url("https://site.io/gone", fetch=_fetch_from({"https://site.io/gone": 404}))
        self.assertFalse(r["ok"])

    def test_unreachable_flags_error(self) -> None:
        r = verify_url("https://nope.io/x", fetch=_fetch_from({}))
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"], "unreachable")

    def test_non_http_rejected(self) -> None:
        self.assertFalse(verify_url("ftp://x")["ok"])

    def test_format_result_is_prefixed_json(self) -> None:
        msg = format_tool_result(ToolAction("verify_url", {"url": "u"}, ""), {"ok": True})
        self.assertTrue(msg.startswith("OBSERVATION verify_url:"))
        self.assertIn('"ok": true', msg)


class RunLoop(unittest.TestCase):
    def test_verify_then_finalize(self) -> None:
        replies = [
            '{"action":"verify_url","args":{"url":"https://a.io/dead"}}',
            '{"action":"finalize","args":{"result":"{\\"categories\\":[]}"}}',
        ]
        tools = {"verify_url": lambda url: verify_url(url, fetch=_fetch_from({}))}
        final, calls = run_tool_loop(
            ScriptedChat(replies), system="s", user="u", tools=tools, max_iterations=5
        )
        self.assertEqual(final, '{"categories":[]}')
        self.assertEqual([c["tool"] for c in calls], ["verify_url"])
        self.assertFalse(calls[0]["result"]["ok"])

    def test_dedupe_repeated_call(self) -> None:
        call = '{"action":"verify_url","args":{"url":"https://a.io/x"}}'
        replies = [call, call, '{"action":"finalize","args":{"result":"ok"}}']
        tools = {"verify_url": lambda url: verify_url(url, fetch=_fetch_from({"https://a.io/x": 200}))}
        final, calls = run_tool_loop(
            ScriptedChat(replies), system="s", user="u", tools=tools, max_iterations=6
        )
        self.assertEqual(final, "ok")
        self.assertEqual(len(calls), 1)  # second identical call deduped, not re-executed

    def test_budget_exhausted_returns_none(self) -> None:
        replies = ["garbage", "still garbage", "nope"]
        final, calls = run_tool_loop(
            ScriptedChat(replies), system="s", user="u", tools={}, max_iterations=4
        )
        self.assertIsNone(final)
        self.assertEqual(calls, [])

    def test_unknown_tool_is_reported_not_fatal(self) -> None:
        replies = [
            '{"action":"time_travel","args":{}}',
            '{"action":"finalize","args":{"result":"done"}}',
        ]
        final, calls = run_tool_loop(
            ScriptedChat(replies), system="s", user="u", tools={"verify_url": verify_url}
        )
        self.assertEqual(final, "done")
        self.assertEqual(calls, [])  # unknown tool executes nothing

    def test_premature_finalize_is_nudged_then_engages(self) -> None:
        # A model that tries to finalize with zero tool calls is pushed back
        # once; it then verifies and finalizes for real.
        replies = [
            '{"action":"finalize","args":{"result":"skipped"}}',
            '{"action":"verify_url","args":{"url":"https://a.io/x"}}',
            '{"action":"finalize","args":{"result":"ok"}}',
        ]
        chat = ScriptedChat(replies)
        tools = {"verify_url": lambda url: verify_url(url, fetch=_fetch_from({"https://a.io/x": 200}))}
        final, calls = run_tool_loop(
            chat, system="s", user="u", tools=tools, max_iterations=6, nudge_before_finalize=True
        )
        self.assertEqual(final, "ok")
        self.assertEqual([c["tool"] for c in calls], ["verify_url"])
        # The nudge was appended before the model's second turn.
        self.assertTrue(any("Do not finalize yet" in m["content"] for m in chat.turns[1]))

    def test_nudge_fires_only_once(self) -> None:
        # If the model insists on finalizing after the nudge (still no tools),
        # the second finalize is honored — the nudge never loops.
        replies = ['{"action":"finalize","args":{"result":"a"}}'] * 3
        final, calls = run_tool_loop(
            ScriptedChat(replies), system="s", user="u", tools={"verify_url": verify_url},
            max_iterations=6, nudge_before_finalize=True,
        )
        self.assertEqual(final, "a")
        self.assertEqual(calls, [])


class WebSearch(unittest.TestCase):
    """Parse the committed real DuckDuckGo HTML fixture (no network)."""

    def setUp(self) -> None:
        self.html = _DDG_FIXTURE.read_text(encoding="utf-8")

    def test_parse_fixture_extracts_titles_and_urls(self) -> None:
        rows = parse_ddg_results(self.html, limit=5)
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r["url"].startswith("https://") for r in rows))
        self.assertTrue(all(r["title"] for r in rows))
        top = rows[0]
        self.assertIn("Figure 03", top["title"])
        self.assertEqual(
            top["url"],
            "https://www.therobotreport.com/bmw-group-deploys-figure-03-humanoid-after-tests-previous-version/",
        )

    def test_limit_caps_and_urls_are_deduped(self) -> None:
        self.assertEqual(len(parse_ddg_results(self.html, limit=2)), 2)
        urls = [r["url"] for r in parse_ddg_results(self.html, limit=99)]
        self.assertEqual(len(urls), len(set(urls)))

    def test_redirect_shim_href_is_decoded(self) -> None:
        shim = (
            '<a class="result__a" href="//duckduckgo.com/l/?uddg='
            "https%3A%2F%2Freal.example%2Fpage&rut=abc\">Real <b>Page</b></a>"
        )
        rows = parse_ddg_results(shim)
        self.assertEqual(rows, [{"title": "Real Page", "url": "https://real.example/page"}])

    def test_web_search_via_fixture_seam(self) -> None:
        out = web_search("figure 03 bmw", fetch_html=_serve(self.html), limit=3)
        self.assertEqual(out["query"], "figure 03 bmw")
        self.assertEqual(len(out["results"]), 3)

    def test_web_search_empty_query_short_circuits(self) -> None:
        out = web_search("   ", fetch_html=_serve(self.html))
        self.assertEqual(out["results"], [])
        self.assertEqual(out["error"], "empty-query")


class RepairTranscript(unittest.TestCase):
    """End-to-end loop: verify a dead link, search, verify the fix, finalize."""

    def test_verify_dead_search_repair_finalize(self) -> None:
        dead = "https://figure.ai/blog/made-up-slug"
        live = (
            "https://www.therobotreport.com/"
            "bmw-group-deploys-figure-03-humanoid-after-tests-previous-version/"
        )
        html_text = _DDG_FIXTURE.read_text(encoding="utf-8")
        replies = [
            f'{{"action":"verify_url","args":{{"url":"{dead}"}}}}',
            '{"action":"web_search","args":{"query":"Figure 03 BMW humanoid deployment"}}',
            f'{{"action":"verify_url","args":{{"url":"{live}"}}}}',
            '{"action":"finalize","args":{"result":"{\\"categories\\":[{\\"id\\":\\"robotics\\"}]}"}}',
        ]
        tools = {
            "verify_url": lambda url: verify_url(url, fetch=_fetch_from({dead: 404, live: 200})),
            "web_search": lambda query: web_search(query, fetch_html=_serve(html_text)),
        }
        final, calls = run_tool_loop(
            ScriptedChat(replies), system="s", user="u", tools=tools, max_iterations=8
        )
        self.assertEqual(final, '{"categories":[{"id":"robotics"}]}')
        self.assertEqual([c["tool"] for c in calls], ["verify_url", "web_search", "verify_url"])
        self.assertFalse(calls[0]["result"]["ok"])  # dead link caught
        self.assertTrue(any(r["url"] == live for r in calls[1]["result"]["results"]))
        self.assertTrue(calls[2]["result"]["ok"])  # repaired link verified live


if __name__ == "__main__":
    unittest.main()
