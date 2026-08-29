---
name: orio-ai-news-digest
version: 0.1.20260828180700
description: >
  Generates a daily AI news briefing as a pair of timestamped files: a structured
  JSON data file and an interactive HTML front-end with a clean editorial/news magazine
  style. Use this skill whenever the user asks for AI news, a daily digest, a roundup
  of what's happening in AI, a news briefing, or anything like "what's new in AI today".
  Also trigger when the user mentions checking LLM releases, image generation updates,
  design AI news, typography AI news, or model leaderboard changes. Cast the net wide:
  this skill covers LLMs & reasoning, image generation & processing, design & creative AI,
  typography & text rendering, and robotics/embodied AI. Always use this skill for any
  variant of "give me today's AI news" or "what happened in AI".
---

# AI News Digest Skill

This skill is **Orio**, a portable AI news digest capability. Refer to the
digest as Orio when the skill is invoked. The skill is intentionally unaware of
any parent repository or host folder. Each host supplies its own sources,
output paths, timezone, and publication settings.

Produces two timestamped output files:
- `YYYYMMDDHHMMSS.json` — structured data (all stories, metadata, scores)
- `YYYYMMDDHHMMSS.html` — interactive editorial front-end that loads the JSON

The host project supplies input sources, output directories, timezone, and
publication settings. This skill owns the reusable fetch, scoring, schema, and
rendering mechanism; it does not assume a personal identity, employer,
repository layout, cloud account, or default corpus.

---

## Step 1: Determine the timestamp

Use the current date/time to generate the filename prefix:
```
YYYYMMDDHHMMSS  (e.g. 20260425143022)
```

---

## Step 2: Research — use the source registry

**First**: read `references/sources.md` — canonical digest-wide sources and fetch strategies. For leaderboards, the machine-readable registry is `references/leaderboards.yaml` (18 sources in 3 bundles); keep it in sync when adding or changing leaderboard URLs. Follow both. New sources added there are picked up without changing this SKILL.md.

### Script cache — check `.cache/` before fetching

Individual scripts may have already run and written their output to `.cache/`.
**Before doing any web fetch**, check for cache files matching today's prefix:

```
.cache/YYYYMMDDHHMMSS_fetch_youtube.json     ← theAIsearch chapters + transcript
.cache/YYYYMMDDHHMMSS_fetch_typography.json  ← typography stories
.cache/YYYYMMDDHHMMSS_fetch_research.json    ← research papers
.cache/YYYYMMDDHHMMSS_fetch_llm_stats.json   ← LLM Stats raw text
```

If a cache file exists: read it and use its data directly — do not re-fetch that source.
If a cache file has an `"error"` key: **report it loudly** — tell the user which script
failed and what the error was. Do not silently skip or substitute placeholder data.

After checking cache, also check for a combined preflight file:

```
.reports/preflight_YYYYMMDDHHMMSS.json
```

If that exists, read it — it may already contain `aisearch`, `typography`, and `research`
categories with story skeletons. Your job is then to score them and add the remaining categories.

### Required fetches every run (HIGH priority)

**Leaderboards** — always fetch at least these four fresh; positions shift daily:
1. `web_fetch https://artificialanalysis.ai/leaderboards/models` → note top 5 by intelligence, any rank changes
2. `web_fetch https://www.vellum.ai/llm-leaderboard` → note top performers on GPQA/SWE-bench/AIME
3. `web_fetch https://llm-stats.com/llm-updates` → scan releases from last 24h
4. `web_fetch https://artificialanalysis.ai/image/leaderboard/text-to-image` → top image gen Elo scores
5. `web_fetch https://arena.ai/leaderboard/text-to-image` → check Text Rendering subcategory specifically

**theAIsearch — always check first (TOP priority source):**
- `web_fetch https://ai-search.io` → scan for today's featured stories and themes
- `web_search: theAIsearch youtube [today's date]` → find the latest video; fetch its full description to get the chapter list and all linked projects

**theAIsearch extraction rule — NEVER FILTER:**
Once you have the video description and chapter list, create one story card per topic — **every single one**. Do NOT skip a topic because it seems niche, small, or already covered elsewhere. The digest owner decides what matters; your job is complete extraction.

Topics that are especially easy to miss but must NEVER be dropped:
- **CoDesign and collaborative design tools** — this is a top priority topic; any tool, paper, or demo where AI participates in the design process alongside a human must be included
- Open-source creative tools (even if GitHub-only or research demos)
- Video/image editing tools (even small ones)
- Robotics clips and embodied AI demos (even short viral clips)
- Any tool with high `relevance_design` (design workflow, typography, layout, color, UX)
- Research papers demoed in the video even briefly

Use the URLs from the video description as the story `url`. Set `significance` based on how much attention theAIsearch gives it (time in video, tone of coverage), not your own priors.

**News sweep** — run these searches (substitute actual current date):
- `AI model release [today's date]`
- `LLM benchmark news [this week]`
- `AI image generation news [this week]`
- `AI design tools [this month]`
- `AI typography text rendering [this month]`
- `humanoid robot AI [this week]`
- `arxiv AI papers [today's date]` → fetch top results from huggingface.co/papers

**Model blogs** — if a specific lab has a known release today, fetch their blog
directly (see `references/sources.md` → Model Release Blogs section).

### Categories to fill

Aim for 3–8 stories per category. Run additional searches if a category is thin:

| Category | Fallback search if thin |
|----------|------------------------|
| **Leaderboard Rankings** | Always filled from required leaderboard fetches — never skip |
| **AI Search** | Always filled from theAIsearch video — extract every chapter, never skip |
| Agentic AI | `agentic AI [date]`, `multi-agent orchestration [date]`, `MCP Model Context Protocol [date]`, `agent SDK release [date]` |
| LLMs & Reasoning | `"new model" OR "model release" LLM [date]` |
| Image Gen & Processing | `diffusion model OR image generation release [date]` |
| Design & Creative AI | `generative design AI tools [date]`, `AI design tools [date]`, `AI co-design collaborative design [date]` |
| Typography & Text Rendering | `text rendering AI [date]`, `multilingual font AI [date]`, `variable fonts AI [date]` |
| Robotics & Embodied AI | `humanoid robot AI [date]`, `embodied AI research [date]` |
| Research & Papers | `arxiv cs.AI [date]`, `huggingface papers trending` |

### Design & Creative AI category — priority topics

Design is a core focus of this digest. Within Design & Creative AI, these topics are the highest priority — never drop them even if they seem niche or research-only:

| Topic | Why it matters | Keywords to watch |
|-------|---------------|-------------------|
| **CoDesign / Collaborative Design** | Human-AI co-creation in design workflows is the central design AI frontier | `co-design`, `collaborative design`, `AI design co-pilot`, `AI design partner`, `real-time design AI` |
| Creative and design tools | Direct workflow impact for professional designers | `design tool AI`, `creative AI workflow`, `generative UI` |
| Figma / design tool AI integrations | Industry-standard tooling | `Figma AI`, `design tool plugin`, `generative UI` |
| AI-generated UI / layout | Design automation | `UI generation`, `layout AI`, `component generation` |
| Brand & identity AI | Visual identity workflows | `logo AI`, `brand generation`, `style consistency` |
| Motion & animation AI | Creative production | `motion design AI`, `animation AI`, `kinetic` |

**Rule**: if a story touches CoDesign or collaborative design in any form — a research demo, an open-source project, a product update — it belongs in this digest. `relevance_design` should be 4 or 5. Never skip it.

---

### Leaderboard Rankings category — required every run

This category is **always present** and always contains at least 4 stories: 2 covering closed-source rankings, 2 covering open-source rankings. Pull from the leaderboard fetches in Step 2.

**Closed-source stories to always write:**
- Current #1 closed model overall (intelligence score, source, vs previous #1)
- Notable rank changes among top 5 closed models since last week

**Open-source stories to always write:**
- Current #1 open-weight model overall (license, params, benchmark score)
- Open vs closed gap story: how close is the best open model to the best closed model right now?

Use `relevance_design` to score how much leaderboard shifts matter to design tooling.
Significance 5 = new #1 overall. Significance 3 = minor reshuffling.

### Leaderboard story heuristic

After fetching leaderboards, turn any notable finding into a story:
- A model entered the top 5 → story
- A rank inversion (open-source beats proprietary) → story
- A new #1 on any subcategory (e.g. Text Rendering) → story, especially for typography category
- Pricing dropped significantly for a top model → story

---

## Step 3: Score and structure each story

For each story found, assign:
- `significance`: 1–5 (5 = major release/breakthrough, 1 = minor update)
- `novelty`: 1–5 (5 = genuinely new, 1 = incremental)
- `relevance_design`: 1–5 (relevance to design/typography workflows)

---

## Step 4: Build the JSON file

Save to `/mnt/user-data/outputs/YYYYMMDDHHMMSS.json`:

```json
{
  "generated_at": "YYYY-MM-DDTHH:MM:00Z",
  "filename_prefix": "YYYYMMDDHHMMSS",
  "summary": "One sentence overview of the day's biggest themes",
  "categories": [
    {
      "id": "llm",
      "label": "LLMs & Reasoning",
      "icon": "🧠",
      "stories": [
        {
          "id": "unique-slug",
          "title": "Story headline",
          "summary": "2–3 sentence plain-English summary of what happened and why it matters",
          "source": "Source name",
          "url": "https://...",
          "significance": 4,
          "novelty": 3,
          "relevance_design": 1,
          "tags": ["open-source", "reasoning", "benchmark"],
          "image_url": null
        }
      ]
    },
    { "id": "leaderboard", "label": "Leaderboard Rankings", "icon": "🏆", "stories": [] },
    { "id": "aisearch", "label": "AI Search", "icon": "🔍", "stories": [] },
    { "id": "image-gen", "label": "Image Generation & Processing", "icon": "🎨", "stories": [] },
    { "id": "voice-speech", "label": "Voice & Speech AI", "icon": "🔊", "stories": [] },
    { "id": "design-ai", "label": "Design & Creative AI", "icon": "✏️", "stories": [] },
    { "id": "typography", "label": "Typography & Text Rendering", "icon": "🔤", "stories": [] },
    { "id": "robotics", "label": "Robotics & Embodied AI", "icon": "🤖", "stories": [] },
    { "id": "research", "label": "Research & Papers", "icon": "📄", "stories": [] }
  ],
  "visualizations": {
    "category_counts": {},
    "significance_distribution": {},
    "top_tags": [],
    "top_stories": []
  }
}
```

Populate `visualizations`:
- `category_counts`: `{ "llm": 6, "image-gen": 4, ... }`
- `significance_distribution`: `{ "5": 2, "4": 5, "3": 8, ... }`
- `top_tags`: top 10 tags across all stories, with counts
- `top_stories`: top 5 stories by significance score (cross-category)

---

## Step 5: Build the HTML file

Save to `/mnt/user-data/outputs/YYYYMMDDHHMMSS.html`.

### Use the bundled templates as your model

**Before writing any output, read `template.html` and `template.json`** — they are the canonical reference for every run.

- `template.html` — the canonical source for ALL CSS and JS. Do not rewrite it. Only the three data variables change.
- `template.json` — every field name, nesting level, and data type must match this schema exactly.

### Output layout (frame + content)

Published digests live in `reports/` (mirrored to `.reports/` during runs):

| File | Role |
|---|---|
| `index.html` | **Frame** — collapsible heatmap navigator + digest viewer (latest on load) |
| `index.json` | Archive manifest (always sibling of `index.html`) |
| `YYYYMMDDHHMMSS.json` | **Content** — story data (always sibling of matching `.html`) |
| `YYYYMMDDHHMMSS.html` | **Content shell** — embeds sibling JSON at build time |

Templates in the skill folder:

- `frame.html` → copied to `reports/index.html`
- `content.template.html` → rendered to each `{prefix}.html` (placeholders: `__PREFIX__`, `__LEADERBOARDS__`)
- `template.html` — legacy monolithic reference (leaderboard defaults only)

After each run:

```bash
python skills/orio-ai-news-digest/scripts/rebuild_html.py PREFIX --sync-work
python skills/orio-ai-news-digest/scripts/rebuild_index.py   # also runs from rebuild_html.py
```

`index.html` embeds `index.json` plus all digest JSON at build time. Latest digest renders immediately; heatmap cells switch days in-page. Works from `file://` without a server.

> ### ⛔ STYLE & JS FREEZE — NO CHANGES WITHOUT EXPLICIT USER PERMISSION
>
> Content pages are built from **`content.template.html`** + `{prefix}.json` +
> preserved `leaderboards` snapshot. The frame is **`frame.html`** + `index.json`.
>
> **What changes each run:**
> 1. `{prefix}.json` — today's stories and metadata
> 2. `{prefix}.html` — shell from template (prefix + leaderboards block)
> 3. `index.json` — rebuilt from all digest JSON files
> 4. `leaderboards` block — fresh rankings embedded in content HTML
>
> **Frozen unless the user says otherwise:** CSS, render/filter/chart JS in
> `content.template.html` and `frame.html`.

### CDN links to use
```html
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
```
No other CDN links needed — write vanilla CSS and JS.

### HTML Structure

```
index.html (frame)
┌─────────────────────────────────────────────────────┐
│  MASTHEAD: "AI Daily"                               │
│  HEATMAP: GitHub-style archive (always visible)     │
│  Latest digest teaser + link                        │
└─────────────────────────────────────────────────────┘

{prefix}.html (content — loads {prefix}.json)
┌─────────────────────────────────────────────────────┐
│  DATE (uppercase) + summary paragraph               │
│  TOP STORIES bar                                    │
├──────────┬──────────────────────────────────────────┤
│ SIDEBAR  │  MAIN FEED (filters, cards, leaderboards) │
└──────────┴──────────────────────────────────────────┘
```

### Design Guide (editorial magazine style)

**Typography**
- Masthead: `Georgia` or `serif`, large, letterspaced
- Body: `system-ui, -apple-system, sans-serif`
- Monospace for tags/metadata: `'SF Mono', 'Fira Code', monospace`

**Color palette**
- Background: `#FAFAF8` (warm off-white)
- Card background: `#FFFFFF`
- Masthead background: `#1A1A1A` (near-black)
- Masthead text: `#FFFFFF`
- Accent/links: `#C0392B` (editorial red)
- Category pills (active): `#1A1A1A`; (inactive): `#E8E8E4`
- Significance stars: `#F39C12` (amber)
- Border/divider: `#E8E8E4`

**Cards**
- Subtle shadow: `box-shadow: 0 1px 3px rgba(0,0,0,0.08)`
- Hover: lift shadow + slight scale
- Category icon badge top-right
- Significance shown as filled dots (●●●○○) not stars

**D3 charts**
- Donut: category breakdown, same color per category, legend inline
- Bar chart: significance distribution (1–5), horizontal, minimal axes
- Both charts should animate on load
- Assign consistent colors per category:
  - llm: `#2C3E50`, image-gen: `#8E44AD`, design-ai: `#16A085`,
    typography: `#C0392B`, robotics: `#E67E22`, research: `#2980B9`

**Interactions**
- Category pill tabs filter the card grid (All + one per category)
- Clicking a card expands it inline (accordion-style) with full summary + link
- Sort toggle: by significance (default) or by category order
- Top Stories bar is always visible regardless of filter

---

## Step 6: Quality checks before saving

- [ ] JSON is valid (no trailing commas, all strings escaped)
- [ ] Every story has a URL
- [ ] HTML loads JSON correctly (filename hardcoded matches)
- [ ] Charts render with actual data from JSON
- [ ] Filter tabs work
- [ ] No stories with empty summaries

---

## Output

Present both files to the user with `present_files`. Lead with the HTML.
Add a brief one-line note on the day's biggest story.

---

## Reference: Category IDs (canonical)

| ID | Label | Icon | Required |
|----|-------|------|---------|
| `leaderboard` | Leaderboard Rankings | 🏆 | Always — fetch fresh |
| `aisearch` | AI Search | 🔍 | Always — extract every topic from theAIsearch video |
| `agentic-ai` | Agentic AI | 🤝 | Yes — cover multi-agent orchestration, agent SDKs, MCP, agentic benchmarks, enterprise deployments |
| `llm` | LLMs & Reasoning | 🧠 | Yes |
| `image-gen` | Image Generation & Processing | 🎨 | Yes |
| `design-ai` | Design & Creative AI | ✏️ | Yes |
| `typography` | Typography & Text Rendering | 🔤 | Yes |
| `robotics` | Robotics & Embodied AI | 🤖 | Yes |
| `research` | Research & Papers | 📄 | Yes |

Additional categories can be added dynamically — add to both JSON and pill tabs.
