"""Shared source discovery for all backends.

Fetches from configured sources: RSS, YouTube, web scrape, structured JSON APIs.
Falls back to MVP (arXiv) if discovery fails.
"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List

from .models import NewsItem


def fetch_from_discovery_skill() -> List[NewsItem]:
    """Call source_discovery skill to fetch from all configured sources.
    
    Returns:
        List of NewsItem, or empty list if skill not available
    """
    skill_script = Path(__file__).parents[2] / "skills" / "source_discovery" / "scripts" / "discover.py"
    config_file = Path(__file__).parents[2] / "config" / "project.yaml"

    if not skill_script.exists() or not config_file.exists():
        return []

    try:
        result = subprocess.run(
            [sys.executable, str(skill_script), "--config", str(config_file)],
            capture_output=True,
            text=True,
            timeout=120,  # 2 min timeout for all sources
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            items = []
            for item_dict in data:
                try:
                    items.append(NewsItem(**item_dict))
                except (ValueError, TypeError):
                    # Skip invalid items
                    pass
            return items
    except Exception:
        pass

    return []


def _parse_rss(data: bytes, source_id: str, limit: int = 20) -> List[NewsItem]:
    """Parse RSS 2.0 or Atom feed."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []

    items = []
    _NS = "http://www.w3.org/2005/Atom"

    def _t(el):
        return (el.text or "").strip() if el is not None else ""

    # Try RSS 2.0
    channel = root.find("channel")
    if channel is not None:
        for el in channel.findall("item"):
            title, url = _t(el.find("title")), _t(el.find("link"))
            summary = _t(el.find("description"))
            if title and url and url.startswith("http"):
                try:
                    items.append(NewsItem(source_id, title, url, summary[:500]))
                except ValueError:
                    pass
            if len(items) >= limit:
                break
        return items

    # Try Atom
    for el in root.findall(f"{{{_NS}}}entry"):
        title = _t(el.find(f"{{{_NS}}}title"))
        url = ""
        for link in el.findall(f"{{{_NS}}}link"):
            href = link.get("href", "")
            if href.startswith("http"):
                url = href
                break
        summary = _t(el.find(f"{{{_NS}}}summary")) or _t(el.find(f"{{{_NS}}}content"))
        if title and url:
            try:
                items.append(NewsItem(source_id, title, url, summary[:500]))
            except ValueError:
                pass
        if len(items) >= limit:
            break

    return items


def fetch_rss_fallback() -> List[NewsItem]:
    """Fallback: fetch from key RSS sources directly."""
    sources = [
        ("openai-blog", "https://openai.com/news/rss.xml"),
        ("anthropic-news", "https://www.anthropic.com/news/rss.xml"),
        ("google-deepmind-blog", "https://deepmind.google/blog/rss.xml"),
        ("arxiv-cs-ai", "https://arxiv.org/rss/cs.AI"),
        ("arxiv-cs-lg", "https://arxiv.org/rss/cs.LG"),
        ("arxiv-cs-cl", "https://arxiv.org/rss/cs.CL"),
    ]

    all_items = []
    for source_id, url in sources:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
            items = _parse_rss(data, source_id, limit=15)
            all_items.extend(items)
        except Exception:
            pass

    return all_items


def fetch_all_sources() -> List[NewsItem]:
    """Fetch from all configured sources.
    
    Strategy:
    1. Try source_discovery skill (all sources + security gate)
    2. Fallback to key RSS feeds
    3. Fallback to MVP stub data
    
    Returns:
        List of NewsItem (never empty - always has fallback)
    """
    # Try source discovery skill first
    items = fetch_from_discovery_skill()
    if items:
        return items

    # Fallback to RSS feeds
    items = fetch_rss_fallback()
    if items:
        return items

    # Last resort: stub data (same as fully_scripted)
    return _stub_items()


def _stub_items() -> List[NewsItem]:
    """Hardcoded stub data for offline testing."""
    return [
        NewsItem(
            "arxiv",
            "Llama 3.1 405B Reaches State-of-the-Art Performance",
            "https://arxiv.org/abs/2407.21022",
            "Meta's latest LLM demonstrates breakthrough improvements in reasoning and multilingual understanding.",
        ),
        NewsItem(
            "arxiv",
            "Vision Transformers Show Strong Zero-Shot Transfer Learning",
            "https://arxiv.org/abs/2407.20299",
            "ViT models maintain performance across diverse visual domains.",
        ),
        NewsItem(
            "arxiv",
            "Scaling Laws for Neural Language Models Revisited",
            "https://arxiv.org/abs/2407.20322",
            "Compute-optimal scaling reveals new patterns in LLM training efficiency.",
        ),
        NewsItem(
            "arxiv",
            "Retrieval-Augmented Generation Improves Hallucination Control",
            "https://arxiv.org/abs/2407.18872",
            "RAG techniques significantly reduce factual errors in LLM outputs.",
        ),
        NewsItem(
            "arxiv",
            "Self-Supervised Learning Advances Enable New Benchmark Records",
            "https://arxiv.org/abs/2407.19234",
            "SSL methods achieve competitive performance with supervised approaches on ImageNet.",
        ),
        NewsItem(
            "arxiv",
            "Graph Neural Networks for Molecular Property Prediction",
            "https://arxiv.org/abs/2407.18765",
            "GNN-based models outperform traditional methods in drug discovery benchmarks.",
        ),
        NewsItem(
            "arxiv",
            "Efficient Fine-Tuning with LoRA Achieves Near-Full-Model Performance",
            "https://arxiv.org/abs/2407.19223",
            "Low-rank adaptation reduces memory requirements while maintaining model quality.",
        ),
        NewsItem(
            "arxiv",
            "Multimodal Transformers Excel at Vision-Language Understanding",
            "https://arxiv.org/abs/2407.18934",
            "End-to-end multimodal models show state-of-the-art results on VQA and captioning.",
        ),
        NewsItem(
            "arxiv",
            "Continuous Learning Algorithms Enable Lifelong Model Adaptation",
            "https://arxiv.org/abs/2407.19012",
            "New continual learning methods prevent catastrophic forgetting.",
        ),
        NewsItem(
            "arxiv",
            "Attention Mechanisms Achieve New Efficiency Records with Sparse Kernels",
            "https://arxiv.org/abs/2407.18823",
            "Sparse attention patterns reduce computational complexity without sacrificing performance.",
        ),
    ]
