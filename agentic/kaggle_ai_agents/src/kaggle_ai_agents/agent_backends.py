"""Pluggable agent backends for the daily brief workflow.

Supports multiple agent execution strategies:
- DirectScript: Hardcoded orchestration (fast, deterministic, for testing)
- GoogleADK: ADK-style agent with instruction + tools
- OllamaAgent: Local Ollama LLM-based agent (requires local Ollama running)

Use config (project.yaml) to select the active backend and its parameters.
"""

from __future__ import annotations

import json
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from kaggle_ai_agents.models import DailyBrief, NewsItem


class AgentBackend(ABC):
    """Abstract base for agent backends."""

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        """Initialize agent backend.

        Args:
            name: Agent backend name (e.g., "direct_script", "google_adk", "ollama")
            config: Backend-specific configuration dict
        """
        self.name = name
        self.config = config or {}

    @abstractmethod
    def forward(self, prompt: str, use_real_sources: bool = True) -> DailyBrief:
        """Execute agent forward pass and return brief.

        Args:
            prompt: User prompt for the agent
            use_real_sources: Whether to fetch from real sources or use stubs

        Returns:
            DailyBrief: Generated 10-card brief
        """
        pass


class DirectScriptBackend(AgentBackend):
    """Direct scripted orchestration (deterministic, fast for testing)."""

    def forward(self, prompt: str, use_real_sources: bool = True) -> DailyBrief:
        """Execute workflow via direct script calls."""
        from kaggle_ai_agents.tools.news_sources import discover_items, fetch_contract_stub_items
        from kaggle_ai_agents.tools.selection import rank_items
        from kaggle_ai_agents.models import BriefCard

        # Phase 1: Source discovery
        if use_real_sources:
            items = discover_items()
        else:
            items = fetch_contract_stub_items()

        # Phase 2: Deduplication and ranking
        ranked_items = rank_items(items)

        # Phase 3: Brief synthesis
        cards = [
            BriefCard(rank=i + 1, title=item.title, url=item.url, why_it_matters=item.summary)
            for i, item in enumerate(ranked_items)
        ]

        from datetime import date
        return DailyBrief(date=str(date.today()), theme="AI signal over noise", cards=cards)


class GoogleADKBackend(AgentBackend):
    """Google ADK-style agent with instruction-driven orchestration."""

    def forward(self, prompt: str, use_real_sources: bool = True) -> DailyBrief:
        """Execute workflow via ADK agent orchestrator."""
        from kaggle_ai_agents.adk_agent import create_agent

        agent = create_agent(
            name="ai_digest",
            instruction=self.config.get("instruction", ""),
            use_real_sources=use_real_sources,
        )

        return agent.forward(prompt)


class OllamaBackend(AgentBackend):
    """Local Ollama LLM-based agent (requires local Ollama running)."""

    def forward(self, prompt: str, use_real_sources: bool = True) -> DailyBrief:
        """Execute workflow via Ollama LLM agent."""
        # Import here to avoid hard dependency on ollama package
        try:
            import ollama
        except ImportError:
            raise RuntimeError(
                "ollama package not installed. Install with: pip install ollama"
            )

        from datetime import date
        from kaggle_ai_agents.models import BriefCard
        from kaggle_ai_agents.tools.news_sources import discover_items, fetch_contract_stub_items
        from kaggle_ai_agents.tools.selection import rank_items

        # Get configuration
        base_url = self.config.get("base_url", "http://localhost:11434")
        model = self.config.get("model", "llama2")
        temperature = self.config.get("temperature", 0.7)
        top_p = self.config.get("top_p", 0.9)

        # Phase 1: Discovery (always script-based for reliability)
        if use_real_sources:
            items = discover_items()
        else:
            items = fetch_contract_stub_items()

        # Phase 2: Ranking (ask Ollama to help rank)
        if items:
            # Build context for Ollama
            items_text = "\n".join(
                [
                    f"- {item.title}: {item.summary}"
                    for item in items[:20]  # Limit to first 20 to avoid token overflow
                ]
            )

            ranking_prompt = f"""Given these AI/ML news items, select the top 10 most important and relevant.
Rank by: breaking news, high impact, broad audience applicability, and technical significance.

Items:
{items_text}

Return ONLY a JSON array with the selected top 10 items (order matters - most important first).
Each item should have: {{"title": str, "url": str, "why_it_matters": str}}
Return only valid JSON, no other text."""

            try:
                client = ollama.Client(host=base_url)
                response = client.generate(
                    model=model,
                    prompt=ranking_prompt,
                    stream=False,
                    options={
                        "temperature": temperature,
                        "top_p": top_p,
                    },
                )
                response_text = response["response"].strip()

                # Try to extract JSON from response
                try:
                    # Find JSON array in response
                    start_idx = response_text.find("[")
                    end_idx = response_text.rfind("]") + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_text = response_text[start_idx:end_idx]
                        selected_data = json.loads(json_text)
                        if isinstance(selected_data, list):
                            cards = [
                                BriefCard(
                                    rank=i + 1,
                                    title=item.get("title", "")[:200],
                                    url=item.get("url", ""),
                                    why_it_matters=item.get("why_it_matters", "")[:500],
                                )
                                for i, item in enumerate(selected_data[:10])
                            ]
                        else:
                            # Fallback to script-based ranking
                            ranked_items = rank_items(items)
                            cards = [
                                BriefCard(
                                    rank=i + 1,
                                    title=item.title,
                                    url=item.url,
                                    why_it_matters=item.summary,
                                )
                                for i, item in enumerate(ranked_items)
                            ]
                    else:
                        # Fallback to script-based ranking
                        ranked_items = rank_items(items)
                        cards = [
                            BriefCard(
                                rank=i + 1,
                                title=item.title,
                                url=item.url,
                                why_it_matters=item.summary,
                            )
                            for i, item in enumerate(ranked_items)
                        ]
                except (json.JSONDecodeError, KeyError, IndexError):
                    # Fallback to script-based ranking on JSON parse error
                    print(
                        "⚠️  Ollama ranking failed (invalid JSON), falling back to script ranking"
                    )
                    ranked_items = rank_items(items)
                    cards = [
                        BriefCard(
                            rank=i + 1,
                            title=item.title,
                            url=item.url,
                            why_it_matters=item.summary,
                        )
                        for i, item in enumerate(ranked_items)
                    ]

            except Exception as e:
                print(f"⚠️  Ollama connection failed ({e}), falling back to script ranking")
                ranked_items = rank_items(items)
                cards = [
                    BriefCard(
                        rank=i + 1,
                        title=item.title,
                        url=item.url,
                        why_it_matters=item.summary,
                    )
                    for i, item in enumerate(ranked_items)
                ]
        else:
            cards = []

        return DailyBrief(date=str(date.today()), theme="AI signal over noise", cards=cards)


def get_agent_backend(backend_name: str, config: dict[str, Any] | None = None) -> AgentBackend:
    """Factory function to get agent backend by name.

    Args:
        backend_name: "direct_script", "google_adk", or "ollama"
        config: Backend-specific configuration

    Returns:
        AgentBackend instance

    Raises:
        ValueError: If backend_name is not recognized
    """
    backends = {
        "direct_script": DirectScriptBackend,
        "google_adk": GoogleADKBackend,
        "ollama": OllamaBackend,
    }

    if backend_name not in backends:
        raise ValueError(
            f"Unknown agent backend: {backend_name}. "
            f"Available: {', '.join(backends.keys())}"
        )

    return backends[backend_name](backend_name, config)


def load_agent_config(config_path: str | None = None) -> tuple[str, dict[str, Any]]:
    """Load agent backend configuration from project.yaml.

    Args:
        config_path: Path to project.yaml (auto-detected if None)

    Returns:
        Tuple of (backend_name, backend_config_dict)

    Raises:
        FileNotFoundError: If config file not found
        KeyError: If agent config section missing
    """
    try:
        import yaml
    except ImportError:
        raise RuntimeError("pyyaml not installed. Install with: pip install pyyaml")

    if config_path is None:
        # Try multiple paths to find project.yaml
        # 1. From this file: src/kaggle_ai_agents/agent_backends.py
        #    Go up 3 levels to get to kaggle_ai_agents root, then config/project.yaml
        current = Path(__file__).parent
        
        # Walk up to find project.yaml
        candidate_paths = [
            current.parent.parent.parent / "config" / "project.yaml",  # From src/kaggle_ai_agents/
            current.parent.parent / "config" / "project.yaml",  # One level up
            current.parent / "config" / "project.yaml",  # Two levels up
        ]
        
        # Also search from cwd if running via pytest
        import sys
        cwd = Path.cwd()
        candidate_paths.extend([
            cwd / "agentic" / "kaggle_ai_agents" / "config" / "project.yaml",
            cwd / "config" / "project.yaml",
        ])
        
        # Walk up from cwd to find run_tests.py as marker
        for parent in cwd.parents:
            candidate_paths.append(parent / "agentic" / "kaggle_ai_agents" / "config" / "project.yaml")
        
        config_path = None
        for path in candidate_paths:
            if path.exists():
                config_path = str(path)
                break
        
        if config_path is None:
            raise FileNotFoundError(
                f"Could not auto-detect project.yaml. "
                f"Checked: {[str(p) for p in candidate_paths[:3]]}"
            )

    with open(config_path) as f:
        config = yaml.safe_load(f)

    agent_config = config.get("agent", {})
    backend_name = agent_config.get("backend", "direct_script")
    backend_config = agent_config.get("backends", {}).get(backend_name, {})

    return backend_name, backend_config
