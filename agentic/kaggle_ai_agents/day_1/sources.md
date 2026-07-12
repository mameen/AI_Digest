# Sources (Day 1)

## Objective

Cast the net as wide as possible while still producing a trustworthy daily brief.
The workflow should ingest broadly, then filter and rank aggressively.

## Source Selection Rules

1. Publicly accessible without paid API keys.
2. Prefer primary sources (original lab, company, benchmark, or paper pages).
3. Stable feed format (RSS or equivalent) when possible; crawler fallback allowed.
4. Clear attribution and linkable original posts.
5. Diverse coverage (labs, ecosystem, benchmarks, policy, dev tools, videos).

## Wide-Net Collection Strategy

1. Ingest many sources into a large candidate pool.
2. Normalize all items into one schema.
3. Deduplicate hard (same event, many outlets).
4. Score by recency, novelty, source trust, and practical relevance.
5. Publish only top cards with traceable links.

This gives broad coverage without overwhelming output.

## AI Search Triple-Path Coverage

For AI search content, collect through three channels in parallel:

1. YouTube channel/videos
   - capture title, description, chapters, and timestamps
2. Website posts/pages
   - crawl article pages and extract canonical links
3. RSS feed (when available)
   - use as low-cost change detection and metadata source

If RSS is unavailable for a source, use website discovery plus YouTube metadata.

## Candidate Source Universe (Day 1)

### A. Labs and Model Providers

1. OpenAI
2. Anthropic
3. Google DeepMind
4. Meta AI
5. Mistral AI
6. Cohere
7. xAI

### B. Cloud and Platform AI Announcements

1. Google Cloud AI
2. Microsoft Azure AI
3. AWS AI and ML

### C. Benchmarks and Evaluation

1. Artificial Analysis
2. SWE-bench
3. EvalPlus
4. LiveBench or equivalent public benchmark feeds

### D. Research and Paper Discovery

1. arXiv (cs.AI, cs.LG, cs.CL)
2. Papers With Code trending
3. Major lab research blogs and release notes

### E. Tooling and Agent Ecosystem

1. LangChain
2. LlamaIndex
3. Hugging Face ecosystem updates
4. Framework release notes (agent/runtime/tooling)

### F. Video-First Signal

1. theAIsearch (YouTube + website + RSS where available)
2. Selected high-signal AI channels with reproducible references

### G. Policy and Governance

1. Official regulator or standards updates relevant to AI deployment
2. Safety institute announcements and policy briefs

## Initial High-Coverage Starter Set (Implement First)

### Lab and Research Updates

1. OpenAI News RSS
   - https://openai.com/news/rss.xml
2. Anthropic News RSS
   - https://www.anthropic.com/news/rss.xml
3. Google DeepMind Blog RSS
   - https://deepmind.google/blog/rss.xml

### Ecosystem and Developer Signal

1. Hugging Face Blog
   - https://huggingface.co/blog
2. LangChain Blog
   - https://blog.langchain.dev/

### Benchmarks and Evaluation Signal

1. Artificial Analysis Leaderboards
   - https://artificialanalysis.ai/
2. SWE-bench Leaderboard Data
   - https://www.swebench.com/
3. EvalPlus Results
   - https://evalplus.github.io/

### Video and Multi-Channel Signal

1. theAIsearch YouTube channel and chapters
2. theAIsearch website posts
3. theAIsearch RSS feed (if published)

## Temporary Exclusions (Until Day 2 Tool Hardening)

1. Sources with unclear licensing or scraping restrictions.
2. High-volume social feeds without strong filtering and rate limits.
3. Sources that frequently break parsing structure.

## Planned Normalized Fields

1. source_id
2. source_url
3. title
4. canonical_url
5. published_at
6. summary
7. category_hint
8. source_channel (rss, website, youtube, api)
9. provenance_token

## Notes

Day 2 will validate each candidate source with tool contracts, failure handling, and parse reliability.
