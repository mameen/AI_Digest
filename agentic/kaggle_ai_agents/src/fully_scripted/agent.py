"""Fully scripted backend: Direct function calls, keyword-based ranking.

No LLM, no framework, pure Python orchestration.
"""

from __future__ import annotations

from datetime import date
from typing import List

from src.base import Agent, NewsItem, BriefCard, DailyBrief
from src.base.sources import fetch_all_sources
from src.base.utils import score_keyword


# ── Discovery ─────────────────────────────────────────────────────────────────

def _parse_rss(data: bytes, source_id: str, limit: int = 20) -> List[NewsItem]:
    """Parse RSS 2.0 or Atom feed."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []

    items = []
    ns_atom = "http://www.w3.org/2005/Atom"

    def _text(el):
        return (el.text or "").strip() if el is not None else ""

    # RSS 2.0
    channel = root.find("channel")
    if channel is not None:
        for el in channel.findall("item"):
            title = _text(el.find("title"))
            url = _text(el.find("link"))
            summary = _text(el.find("description"))
            if title and url and url.startswith("http"):
                try:
                    items.append(NewsItem(source_id, title, url, summary[:500]))
                except ValueError:
                    pass
            if len(items) >= limit:
                break
        return items

    # Atom
    for el in root.findall(f"{{{ns_atom}}}entry"):
        title = _text(el.find(f"{{{ns_atom}}}title"))
        url = ""
        for link in el.findall(f"{{{ns_atom}}}link"):
            href = link.get("href", "")
            if href.startswith("http"):
                url = href
                break
        summary = _text(el.find(f"{{{ns_atom}}}summary")) or _text(el.find(f"{{{ns_atom}}}content"))
        if title and url:
            try:
                items.append(NewsItem(source_id, title, url, summary[:500]))
            except ValueError:
                pass
        if len(items) >= limit:
            break

    return items


def _fetch_mvp_sources() -> List[NewsItem]:
    """MVP: Fetch arXiv only (fallback)."""
    sources = [
        ("arxiv-cs-ai", "https://arxiv.org/rss/cs.AI"),
        ("arxiv-cs-lg", "https://arxiv.org/rss/cs.LG"),
    ]
    all_items = []
    for sid, url in sources:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            items = _parse_rss(data, sid, limit=15)
            all_items.extend(items)
            print(f"  {sid}: {len(items)} items")
        except Exception as e:
            print(f"  {sid}: unavailable ({str(e)[:30]})")
    
    # Fallback: stub data if network fails
    if not all_items:
        print("  ⚠️  Network unavailable, using stub data")
        all_items = _stub_items()
    
    return all_items


def _stub_items() -> List[NewsItem]:
    """Fallback stub data when network unavailable."""
    return [
        NewsItem("arxiv", "Llama 3.1 405B Reaches State-of-the-Art Performance", "https://arxiv.org/abs/2407.21022", "Meta's latest LLM demonstrates breakthrough improvements in reasoning and multilingual understanding."),
        NewsItem("arxiv", "Vision Transformers Show Strong Zero-Shot Transfer Learning", "https://arxiv.org/abs/2407.20299", "ViT models maintain performance across diverse visual domains."),
        NewsItem("arxiv", "Scaling Laws for Neural Language Models Revisited", "https://arxiv.org/abs/2407.20322", "Compute-optimal scaling reveals new patterns in LLM training efficiency."),
        NewsItem("arxiv", "Retrieval-Augmented Generation Improves Hallucination Control", "https://arxiv.org/abs/2407.18872", "RAG techniques significantly reduce factual errors in LLM outputs."),
        NewsItem("arxiv", "Self-Supervised Learning Advances Enable New Benchmark Records", "https://arxiv.org/abs/2407.19234", "SSL methods achieve competitive performance with supervised approaches on ImageNet."),
        NewsItem("arxiv", "Graph Neural Networks for Molecular Property Prediction", "https://arxiv.org/abs/2407.18765", "GNN-based models outperform traditional methods in drug discovery benchmarks."),
        NewsItem("arxiv", "Efficient Fine-Tuning with LoRA Achieves Near-Full-Model Performance", "https://arxiv.org/abs/2407.19223", "Low-rank adaptation reduces memory requirements while maintaining model quality."),
        NewsItem("arxiv", "Multimodal Transformers Excel at Vision-Language Understanding", "https://arxiv.org/abs/2407.18934", "End-to-end multimodal models show state-of-the-art results on VQA and captioning."),
        NewsItem("arxiv", "Continuous Learning Algorithms Enable Lifelong Model Adaptation", "https://arxiv.org/abs/2407.19012", "New continual learning methods prevent catastrophic forgetting."),
        NewsItem("arxiv", "Attention Mechanisms Achieve New Efficiency Records with Sparse Kernels", "https://arxiv.org/abs/2407.18823", "Sparse attention patterns reduce computational complexity without sacrificing performance."),
    ]


# ── Ranking ───────────────────────────────────────────────────────────────────


# ── Agent ─────────────────────────────────────────────────────────────────────

class FullyScriptedAgent(Agent):
    """Direct function calls: discover → rank → validate."""

    def discover(self) -> List[NewsItem]:
        """Fetch from all configured sources."""
        print("\n[discover]")
        items = fetch_all_sources()
        print(f"  → {len(items)} items from {len(set(i.source_id for i in items))} sources")
        return items

    def rank(self, items: List[NewsItem], count: int = 10) -> List[NewsItem]:
        """Keyword-based scoring, no LLM."""
        print("\n[rank]")
        ranked = sorted(items, key=lambda x: (-score_keyword(x), x.title.lower()))
        print(f"  → {len(ranked[:count])} top items ranked (keyword-based, no LLM)")
        return ranked[:count]

    def validate(self, items: List[NewsItem]) -> DailyBrief:
        """Schema validation: ensure exactly 10 cards."""
        print("\n[validate]")

        if len(items) < 10:
            raise ValueError(f"Need 10 items for brief, got {len(items)}")

        cards = [
            BriefCard(
                rank=i + 1,
                title=item.title,
                url=item.url,
                why_it_matters=item.summary[:200] if item.summary else "Key AI/ML story",
            )
            for i, item in enumerate(items[:10])
        ]

        brief = DailyBrief(
            date=str(date.today()),
            theme="AI signal over noise",
            cards=cards,
            schema_version="1.0",
        )

        print(f"  → {len(brief.cards)} cards validated ✅")
        return brief
