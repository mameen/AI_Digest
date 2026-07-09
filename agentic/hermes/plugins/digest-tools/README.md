# digest-tools (Hermes plugin)

One-time install (symlink into Hermes plugin dir):

```bash
ln -sf "$REPO/agentic/hermes/plugins/digest-tools" ~/.hermes/plugins/digest-tools
```

Restart Hermes gateway / workers after linking. Enable toolset **`digest`** on the
`researcher` profile (`setup` does this). Search uses Hermes built-in **`web_search`**
via `web.backend ddgs` (configured by `setup` / `bootstrap`).

Digest plugin tools: `verify_url`, `fetch_rss`, `read_preflight_category`,
`read_crawl_markdown`, `read_structured_json`, `read_topic_config`.

Logic lives in [`../../tools/web.py`](../../tools/web.py) (fork of `llm_pipeline/tools.py`).
