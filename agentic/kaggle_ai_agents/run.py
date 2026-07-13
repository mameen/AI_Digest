#!/usr/bin/env python3
"""Local runner for the AI Digest kaggle agent — NOT the submission.

The Kaggle submission is: submission/kaggle_submission.ipynb

This script exercises the same logic via 3 runtime configs:
  1. fully_scripted   — no LLM, keyword-based ranking (fast, deterministic)
  2. google_adk       — Google Gemini API (requires GEMINI_API_KEY)
  3. fully_on_ollama  — local Ollama (default for local dev)

Usage:
  python run.py                          # uses fully_on_ollama + qwen2.5-coder:14b (default)
  python run.py --config fully_scripted
  python run.py --config google_adk
  python run.py --model qwen3:8b         # override model
  python run.py --host http://localhost:11434    # override host
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from typing import List


# ── Models ────────────────────────────────────────────────────────────────────

@dataclass
class NewsItem:
    source_id: str
    title: str
    url: str
    summary: str = ""

    def __post_init__(self):
        if not self.url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {self.url}")


@dataclass
class BriefCard:
    rank: int
    title: str
    url: str
    why_it_matters: str

    def __post_init__(self):
        assert 1 <= self.rank <= 10, f"Rank must be 1-10, got {self.rank}"
        assert self.url.startswith("https://"), f"URL must be HTTPS: {self.url}"


@dataclass
class DailyBrief:
    date: str
    theme: str
    cards: List[BriefCard]
    schema_version: str = "1.0"

    def __post_init__(self):
        assert len(self.cards) == 10, f"Must have exactly 10 cards, got {len(self.cards)}"


# ── Config registry ───────────────────────────────────────────────────────────

CONFIGS = {
    "fully_scripted": {
        "backend": "script",
        "description": "No LLM — keyword-based ranking (fast, deterministic)",
        "requires": [],
    },
    "google_adk": {
        "backend": "google",
        "description": "Google Gemini API (requires GEMINI_API_KEY env var)",
        "requires": ["GEMINI_API_KEY"],
    },
    "fully_on_ollama": {
        "backend": "ollama",
        "description": "Local Ollama LLM (requires Ollama running)",
        "requires": [],
        "model": "qwen2.5-coder:14b",
        "host": "http://localhost:11434",
    },
}

DEFAULT_CONFIG = "fully_on_ollama"


# ── Discovery ─────────────────────────────────────────────────────────────────

def parse_rss(data: bytes, source_id: str, limit: int = 20) -> List[NewsItem]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    items = []
    _NS = "http://www.w3.org/2005/Atom"

    def _t(el):
        return (el.text or "").strip() if el is not None else ""

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


def fetch_items() -> List[NewsItem]:
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
            items = parse_rss(data, sid, limit=15)
            all_items.extend(items)
            print(f"  {sid}: {len(items)} items")
        except Exception:
            print(f"  {sid}: unavailable")
    return all_items


def fallback_items() -> List[NewsItem]:
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


# ── Ranking backends ──────────────────────────────────────────────────────────

def rank_script(items: List[NewsItem]) -> List[NewsItem]:
    """Fully scripted: keyword-based, no LLM."""
    def score(item):
        s = 0
        text = f"{item.title} {item.summary}".lower()
        if any(k in text for k in ["model", "llm", "agent", "reasoning"]): s += 3
        if any(k in text for k in ["benchmark", "eval"]): s += 3
        if any(k in text for k in ["ai", "ml", "learning"]): s += 2
        return s
    ranked = sorted(items, key=lambda x: (-score(x), x.title.lower()))
    print("  backend: keyword script (no LLM)")
    return ranked[:10]


def rank_google(items: List[NewsItem]) -> List[NewsItem]:
    """Google ADK: calls Gemini API."""
    if not os.getenv("GEMINI_API_KEY"):
        print("  ⚠️  GEMINI_API_KEY not set, falling back to script")
        return rank_script(items)

    try:
        import google.generativeai as genai
        # Note: api_key reads from GEMINI_API_KEY env var, not hardcoded
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        items_text = "\n".join([f"{i+1}. {item.title}" for i, item in enumerate(items)])
        prompt = f"Rank these {len(items)} AI/ML stories (1=most important). Return ONLY comma-separated ranks:\n{items_text}"
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        ranks = [int(x.strip()) for x in response.text.strip().split(",")]
        ranked = [None] * len(items)
        for rank, item in zip(ranks, items):
            if 1 <= rank <= len(items):
                ranked[rank - 1] = item
        result = [i for i in ranked if i is not None][:10]
        print("  backend: Google Gemini API ✅")
        return result
    except Exception as e:
        print(f"  ⚠️  Gemini error: {str(e)[:60]}, falling back to script")
        return rank_script(items)


def rank_ollama(items: List[NewsItem], model: str, host: str) -> List[NewsItem]:
    """Fully on Ollama: local LLM via stdlib urllib."""
    import re
    items_text = "\n".join([f"{i+1}. {item.title}" for i, item in enumerate(items)])
    prompt = (
        f"Rank these {len(items)} AI/ML stories by importance (1=most important). "
        f"Return ONLY comma-separated ranks like: 3,1,2...\n\n{items_text}"
    )
    req_data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=req_data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            result = json.loads(r.read())
        text = result["response"].strip()
        nums = re.findall(r"\d+", text.split("\n")[0])
        ranks = [int(x) for x in nums if 1 <= int(x) <= len(items)]
        if len(ranks) < len(items):
            print(f"  ⚠️  Ollama partial ranks ({len(ranks)}/{len(items)}), falling back to script")
            return rank_script(items)
        ranked = [None] * len(items)
        for rank, item in zip(ranks, items):
            ranked[rank - 1] = item
        result_items = [i for i in ranked if i is not None][:10]
        print(f"  backend: Ollama {model} @ {host} ✅")
        return result_items
    except Exception as e:
        print(f"  ⚠️  Ollama error: {str(e)[:60]}, falling back to script")
        return rank_script(items)


# ── ADK Agent orchestrator ────────────────────────────────────────────────────

class ADKAgent:
    """Single agent: instruction + 3 tools (discover → rank → validate)."""

    def __init__(self, config_name: str, cfg: dict):
        self.config_name = config_name
        self.cfg = cfg

    def tool_discover(self) -> List[NewsItem]:
        print("\n[tool: discover]")
        items = fetch_items()
        if not items:
            print("  network unavailable, using fallback data")
            items = fallback_items()
        print(f"  → {len(items)} items")
        return items

    def tool_rank(self, items: List[NewsItem]) -> List[NewsItem]:
        print("\n[tool: rank]")
        backend = self.cfg["backend"]
        if backend == "ollama":
            return rank_ollama(items, self.cfg.get("model", "qwen3:8b"), self.cfg.get("host", "http://localhost:11434"))
        elif backend == "google":
            return rank_google(items)
        else:
            return rank_script(items)

    def tool_validate(self, items: List[NewsItem]) -> DailyBrief:
        print("\n[tool: validate]")
        cards = [
            BriefCard(rank=i + 1, title=item.title, url=item.url, why_it_matters=item.summary[:200])
            for i, item in enumerate(items)
        ]
        brief = DailyBrief(date=str(date.today()), theme="AI signal over noise", cards=cards)
        print(f"  → {len(brief.cards)} cards validated")
        return brief

    def forward(self) -> DailyBrief:
        items = self.tool_discover()
        ranked = self.tool_rank(items)
        return self.tool_validate(ranked)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="AI Digest local runner (non-submission)")
    parser.add_argument("--config", choices=list(CONFIGS), default=DEFAULT_CONFIG,
                        help=f"Runtime config (default: {DEFAULT_CONFIG})")
    parser.add_argument("--model", default=None, help="Ollama model override (e.g. qwen3:8b)")
    parser.add_argument("--host", default=None, help="Ollama host override (e.g. http://localhost:11434)")
    parser.add_argument("--output", default=None, help="Write brief JSON to file")
    args = parser.parse_args()

    cfg = dict(CONFIGS[args.config])
    if args.model:
        cfg["model"] = args.model
    if args.host:
        cfg["host"] = args.host

    print(f"\n{'='*60}")
    print(f"AI Digest — Local Runner")
    print(f"Config : {args.config}")
    print(f"Desc   : {cfg['description']}")
    if cfg["backend"] == "ollama":
        print(f"Model  : {cfg.get('model', 'qwen3:8b')}")
        print(f"Host   : {cfg.get('host', 'http://localhost:11434')}")
    print(f"{'='*60}")

    # Check requirements
    for req in cfg.get("requires", []):
        if not os.getenv(req):
            print(f"\n❌ Required env var not set: {req}")
            return 1

    agent = ADKAgent(args.config, cfg)
    brief = agent.forward()

    print(f"\n{'='*60}")
    print(f"RESULTS — Top 10 Stories ({args.config})")
    print(f"{'='*60}")
    for card in brief.cards:
        print(f"  [{card.rank:2}] {card.title}")
        print(f"       {card.url}")

    if args.output:
        out = {
            "date": brief.date,
            "config": args.config,
            "theme": brief.theme,
            "schema_version": brief.schema_version,
            "cards": [{"rank": c.rank, "title": c.title, "url": c.url, "why_it_matters": c.why_it_matters} for c in brief.cards],
        }
        with open(args.output, "w") as f:
            json.dump(out, f, indent=2)
        print(f"\n✅ Written to {args.output}")

    print(f"\n✅ Done — {len(brief.cards)} cards, config={args.config}")
    return 0


if __name__ == "__main__":
    # NOT a submission entry point
    raise SystemExit(main())
