# AI News Digest — Source Registry

**Leaderboards (machine-readable):** [`leaderboards.yaml`](leaderboards.yaml) — 3 bundles, 18 sources with fetch strategy and extraction hints. Edit that file to add or change leaderboard sources; the tables below mirror it for human reading.

This file is the canonical list of sources to check for each digest run.
**To add a new source**: append it to the relevant section with the same format.
**To disable a source**: prefix the URL line with `# DISABLED:`.
**Leaderboard sources** should always be fetched fresh — never rely on cached knowledge.

---

## 🏆 LLM Leaderboards — Closed Source
*Proprietary models: GPT, Claude, Gemini, Grok etc. Fetch every run.*

| Name | URL | What it tracks | Fetch strategy |
|------|-----|----------------|----------------|
| Artificial Analysis (All) | https://artificialanalysis.ai/leaderboards/models | Intelligence, speed, price across 100+ models incl. closed | web_fetch — top 5 by intelligence score, note rank changes |
| Vellum LLM Leaderboard | https://www.vellum.ai/llm-leaderboard | GPQA, AIME, SWE-bench, FrontierMath — closed + open | web_fetch — note #1 per benchmark |
| LM Arena (Chatbot Arena) | https://lmarena.ai/leaderboard | Human preference Elo — best real-world proxy for closed models | web_fetch — note #1 and any new entrants |
| BenchLM | https://benchlm.ai | 220 models × 178 benchmarks, weighted scoring | web_search: "benchlm leaderboard today" |
| Onyx LLM Leaderboard | https://onyx.app/llm-leaderboard | Overall/Coding/Math/Chat/Reasoning/Agentic tiers | web_search: "onyx llm leaderboard" |
| PricePerToken Coding LB | https://pricepertoken.com/leaderboards/coding | Coding benchmark + community dev votes | web_fetch — note top coding model |
| LLM Stats | https://llm-stats.com/llm-updates | 24h release tracker, 500+ models | web_fetch — scan all releases in last 24h |

---

## 🏆 LLM Leaderboards — Open Source
*Open-weight models: Llama, DeepSeek, Qwen, Mistral, FLUX etc. Fetch every run.*

| Name | URL | What it tracks | Fetch strategy |
|------|-----|----------------|----------------|
| Vellum Open LLM LB | https://www.vellum.ai/open-llm-leaderboard | Open-weight only: GPQA, AIME, SWE-bench | web_fetch — note top open model and license |
| HuggingFace Open LLM LB | https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard | Community standard open LLM ranking | web_fetch — note #1 and recent entrants |
| Artificial Analysis (Open) | https://artificialanalysis.ai/leaderboards/models | Filter by open-weight — intelligence vs cost | web_fetch — compare best open vs best closed gap |
| LLM Gateway Timeline | https://llmgateway.io/timeline | API availability for open models, newest first | web_fetch — scan top 10 entries |
| LiveBench | https://livebench.ai | Contamination-free tasks, monthly refresh — good for open models | web_fetch — note open model ranking vs closed |
| Papers With Code SOTA | https://paperswithcode.com/sota | Academic SOTA across tasks, heavy open-source coverage | web_search: "papers with code SOTA LLM [date]" |

### Leaderboard story heuristic — open vs closed
Always check and report on the **gap** between open and closed:
- Open model enters top 5 overall → major story (significance 5)
- Open model beats a closed model on a specific benchmark → story
- New open model released under permissive license (Apache/MIT) → story
- Open model achieves parity on coding/math with frontier closed model → story

---

## 🎨 Image Generation Leaderboards
*Fetch at least 2 of these per digest.*

| Name | URL | What it tracks | Fetch strategy |
|------|-----|----------------|----------------|
| Artificial Analysis Image Arena | https://artificialanalysis.ai/image/leaderboard/text-to-image | Elo from blind human votes, text-to-image | web_fetch — top 5 Elo scores |
| Artificial Analysis Image Edit LB | https://artificialanalysis.ai/image/leaderboard/image-edit | Image editing models | web_fetch — top 5 |
| Arena.ai Text-to-Image | https://arena.ai/leaderboard/text-to-image | 57+ models, 5M votes, 8 subcategories incl. Text Rendering | web_fetch — note Text Rendering category specifically |
| Arena.ai Image Edit | https://arena.ai/leaderboard/image-edit | Image editing Elo, 25M+ votes | web_fetch — top 3 |
| JAI Portal Leaderboard | https://www.jaiportal.com/leaderboard | Image + Video + Audio Elo, all modalities | web_fetch — scan for video gen leaders |
| LM Arena Image | https://lmarena.ai/leaderboard/text-to-image | Human preference, all major generators | web_fetch — note rank changes |

---

## 📰 News & Release Trackers
*Scan these for stories daily.*

| Name | URL | Cadence | Priority |
|------|-----|---------|----------|
| **theAIsearch — Web** | https://ai-search.io | Daily | **TOP** — primary inspiration for this digest; always check first |
| **theAIsearch — YouTube** | https://www.youtube.com/@theAIsearch | Daily | **TOP** — scan latest videos for stories missed elsewhere |
| LLM Stats Updates | https://llm-stats.com/llm-updates | Hourly | HIGH |
| Simon Willison's Blog | https://simonwillison.net | Daily | HIGH — best curated AI release notes |
| HuggingFace Papers | https://huggingface.co/papers | Daily | HIGH — arxiv picks with social signal |
| Aisearch Substack | https://aisearch.substack.com | Daily | HIGH |
| Fazm Blog | https://fazm.ai/blog | Weekly+ | MED — good LLM roundups |
| WhatLLM | https://whatllm.org/blog | Weekly | MED |
| TechCrunch AI | https://techcrunch.com/artificial-intelligence | Daily | MED |
| The Verge AI | https://www.theverge.com/ai-artificial-intelligence | Daily | MED |
| MIT Technology Review AI | https://www.technologyreview.com/topic/artificial-intelligence | Daily | MED |

---

## 🔬 Research (arXiv + Papers)
*Check these for significant new papers, especially with code.*

| Name | URL | Search strategy |
|------|-----|----------------|
| arXiv CS.AI | https://arxiv.org/list/cs.AI/recent | web_search: "arxiv cs.ai [date]" or web_fetch |
| arXiv CS.CV | https://arxiv.org/list/cs.CV/recent | Computer vision, image gen architecture |
| arXiv CS.CL | https://arxiv.org/list/cs.CL/recent | NLP, multilingual, text rendering |
| HuggingFace Papers | https://huggingface.co/papers | Social-signal filter: fetch top 10 upvoted |
| Semantic Scholar Trending | https://www.semanticscholar.org/trending | web_search: "semantic scholar trending AI" |

---

## 🤖 Model Release Blogs
*Fetch when a specific lab has a known release.*

| Lab | Blog URL |
|-----|----------|
| OpenAI | https://openai.com/news |
| Anthropic | https://www.anthropic.com/news |
| Google DeepMind | https://deepmind.google/discover/blog |
| Meta AI | https://ai.meta.com/blog |
| Mistral | https://mistral.ai/news |
| DeepSeek | https://api-docs.deepseek.com/news |
| Alibaba / Qwen | https://qwen.ai/blog |
| Kimi / Moonshot | https://www.kimi.com/blog |
| xAI / Grok | https://x.ai/blog |
| Stability AI | https://stability.ai/news |
| Black Forest Labs (FLUX) | https://blackforestlabs.ai/blog |

---

## 🤝 Agentic AI Sources
*Search these every run for the Agentic AI category. Covers multi-agent orchestration, agent SDKs, MCP, benchmarks, and enterprise deployments.*

| Name | URL | What it tracks | Fetch strategy |
|------|-----|----------------|----------------|
| Model Context Protocol | https://modelcontextprotocol.io | MCP spec, server count, adoption milestones | `web_search: "MCP Model Context Protocol [date]"` |
| OpenAI Agents SDK | https://openai.com/index/openai-agents-sdk/ | SDK releases, TypeScript support, Enterprise Workspace Agents | `web_fetch` or `web_search: "OpenAI Agents SDK [date]"` |
| Anthropic Agents | https://www.anthropic.com/news | Claude agentic capabilities, computer use, multi-agent | `web_fetch` |
| Microsoft Semantic Kernel | https://devblogs.microsoft.com/semantic-kernel/ | Agent Framework releases, A2A protocol | `web_search: "Microsoft Agent Framework [date]"` |
| LangChain Blog | https://blog.langchain.dev | LangGraph releases, agent patterns | `web_search: "LangGraph [date]"` |
| BenchLM | https://benchlm.ai | Agentic capability scores, model rankings | `web_search: "benchlm agentic leaderboard"` |
| WildClawBench / OSWorld | https://os-world.github.io | Computer use benchmarks | `web_search: "OSWorld computer use benchmark [date]"` |
| SWE-bench | https://www.swebench.com | Coding agent benchmark — SOTA tracker | `web_search: "SWE-bench SOTA [date]"` |

### Agentic AI search queries — run every digest
```
web_search: "agentic AI [current month year]"
web_search: "multi-agent orchestration [date]"
web_search: "MCP Model Context Protocol [date]"
web_search: "agent SDK release [date]"
web_search: "enterprise agentic AI deployment [date]"
```

### Agentic AI story priority rules
- **New agent SDK release or major version** → significance 4–5
- **MCP adoption milestones** (server count, SDK downloads) → significance 3–4
- **Agentic benchmark SOTA update** (SWE-bench, OSWorld) → significance 3–4, tag `benchmark`
- **Enterprise production deployment** (regulated industry) → significance 4
- **New multi-agent framework GA** → significance 4

---

## 🎙️ YouTube Channels
*Search for recent videos; use web_search with channel name + date.*

| Channel | URL | Search query pattern | Priority |
|---------|-----|---------------------|----------|
| **theAIsearch** | https://www.youtube.com/@theAIsearch | `theAIsearch AI news [date]` | **TOP** — check every run |
| Two Minute Papers | https://www.youtube.com/@TwoMinutePapers | `"two minute papers" [topic] [year]` | MED |
| Yannic Kilcher | https://www.youtube.com/@YannicKilcher | `"yannic kilcher" [topic] [year]` | MED |
| Matt Wolfe | https://www.youtube.com/@mreflow | `"matt wolfe" AI news [date]` | MED |
| TheAIGRID | https://www.youtube.com/@TheAIGRID | `theaigrid AI news [date]` | MED |

---

## 🔤 Typography & Font Sites
*Fetch these every run for the Typography & Text Rendering category. Always look for AI-related content.*

| Name | URL | What it tracks | Fetch strategy |
|------|-----|----------------|----------------|
| **Monotype Blog** | https://www.monotype.com/resources/expertise/typography-terms | Type industry news, AI font tools, Monotype Fonts platform updates | `web_fetch https://www.monotype.com/resources` — scan for AI/ML mentions |
| **Monotype Newsroom** | https://www.monotype.com/newsroom | Press releases, product launches (AI Search, new font tech) | `web_fetch` — check for new announcements |
| **I Love Typography** | https://ilovetypography.com | Type design deep-dives, font releases with cultural context | `web_fetch` — scan latest posts |
| **Typographica** | https://typographica.org | Annual type reviews, significant font releases | `web_fetch` — scan recent reviews |
| **Fonts In Use** | https://fontsinuse.com | Real-world typography, AI-generated typography examples | `web_search: "fonts in use AI typography [year]"` |
| **Google Fonts Knowledge** | https://fonts.google.com/knowledge | Type education + variable font articles | `web_fetch` — scan recent articles |
| **CreativeBloq Typography** | https://www.creativebloq.com/tag/typography | Design press — font tools, AI text rendering news | `web_search: "creativebloq typography AI [date]"` |
| **Type Directors Club** | https://tdc.org/news | Industry awards, type innovation news | `web_fetch` — scan news |
| **MyFonts Blog** | https://www.myfonts.com/pages/blog | Font discovery, new releases, AI search features | `web_fetch` |

### Typography web search queries — run every digest

In addition to `web_fetch` of the sites above, always run these searches:
```
web_search: "typography AI [current month year]"
web_search: "font AI machine learning [current month year]"
web_search: "text rendering AI model [this week]"
web_search: "variable fonts AI [this year]"
web_search: "Monotype AI [current month year]"
web_search: "font discovery AI search [this month]"
web_search: "multilingual font AI [this month]"
```

### Typography story priority rules

- **Monotype AI Search / font discovery tools** → always significance ≥ 4, `relevance_design` 5
- **Text-in-image accuracy improvements** (any model) → significance ≥ 3, tag `text-rendering`
- **Variable font + AI** → significance 3–4, `relevance_design` 5
- **New font released with AI design assistance** → significance 2–3
- **AI leaderboard subcategory: Text Rendering** → cross-post to both `typography` and `leaderboard` categories

---

## ➕ Adding New Sources

When a new leaderboard, tracker, or blog becomes relevant, add it to the appropriate
section above using the same table format. Include:
1. Name + URL
2. What it tracks
3. Fetch strategy (web_fetch URL directly, or web_search query pattern)

The skill will automatically pick up new entries on the next run.

**Suggested additions to evaluate:**
- Scale AI SOTA tracker (when available publicly)
- Epoch AI compute tracker
- Papers With Code leaderboard: https://paperswithcode.com/sota
