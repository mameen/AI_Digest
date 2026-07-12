"""Single-agent workflow stub for the capstone.

This module provides multiple implementations:
1. run_daily_brief() - Scripted orchestration (deterministic, fast tests)
2. run_daily_brief_with_agent() - ADK agent-driven (intent-based, extensible)
3. run_daily_brief_with_backend() - Config-driven agent selection (pluggable backends)

All produce the same DailyBrief output; different backends demonstrate scaling
from hardcoded logic to intent-driven to LLM-based reasoning.

Available backends:
- "direct_script": Hardcoded orchestration (fast, deterministic)
- "google_adk": Google ADK-style agent with tools
- "ollama": Local Ollama LLM-based agent (requires local Ollama running)

Configuration via project.yaml:
    agent:
      backend: "google_adk"  # or "direct_script", "ollama"
      backends:
        ollama:
          base_url: "http://localhost:11434"
          model: "llama2"
          temperature: 0.7
"""

from __future__ import annotations

from datetime import date

from kaggle_ai_agents.agent_backends import get_agent_backend, load_agent_config
from kaggle_ai_agents.models import BriefCard, DailyBrief
from kaggle_ai_agents.tools.news_sources import discover_items, fetch_contract_stub_items
from kaggle_ai_agents.tools.selection import rank_items


def run_daily_brief(use_real_sources: bool = False) -> DailyBrief:
    """Run the daily brief workflow.
    
    Args:
        use_real_sources: If True, fetch from configured sources via discover.py.
                         If False, use stub data (for fast tests).
    """
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
    return DailyBrief(date=str(date.today()), theme="AI signal over noise", cards=cards)


def run_daily_brief_with_agent(use_real_sources: bool = True) -> DailyBrief:
    """Run the daily brief workflow using an ADK agent orchestrator.
    
    This version demonstrates the course's recommended approach:
    - Single agent with instruction
    - Skills as tools
    - Intent-driven orchestration
    
    Args:
        use_real_sources: If True (default), agent fetches from real sources.
                         If False, uses stub data (for fast testing).
    
    Returns:
        DailyBrief: Curated 10-card brief
    """
    from kaggle_ai_agents.adk_agent import create_agent
    
    agent = create_agent(
        name="ai_digest",
        instruction=(
            "You are an AI news curator. Discover the latest AI/ML stories from all "
            "configured sources, deduplicate, rank by importance, and produce a "
            "10-card curated brief. Explain why each story matters."
        ),
    )
    
    # The agent orchestrates tools in logical sequence
    prompt = "Generate today's AI digest from all sources" if use_real_sources else "Use stub data"
    brief = agent.forward(prompt)
    return brief


def run_daily_brief_with_backend(
    backend_name: str | None = None, use_real_sources: bool = True
) -> DailyBrief:
    """Run the daily brief workflow using a configurable backend.
    
    This is the primary entry point for production use. Selects backend from
    project.yaml configuration, or accepts explicit backend override.
    
    Args:
        backend_name: Optional backend override ("direct_script", "google_adk", "ollama").
                     If None, loads from project.yaml configuration.
        use_real_sources: If True (default), fetch from real sources.
                         If False, uses stub data (for fast testing).
    
    Returns:
        DailyBrief: Curated 10-card brief
        
    Raises:
        ValueError: If backend_name is not recognized
        FileNotFoundError: If config file cannot be found
        RuntimeError: If required dependencies missing (e.g., ollama package)
    
    Examples:
        # Use configured backend from project.yaml
        brief = run_daily_brief_with_backend()
        
        # Override backend
        brief = run_daily_brief_with_backend("ollama")
        
        # Use fast stubs for testing
        brief = run_daily_brief_with_backend(use_real_sources=False)
    """
    # Load backend config if not explicitly provided
    if backend_name is None:
        backend_name, backend_config = load_agent_config()
        print(f"📌 Loaded backend from config: {backend_name}")
    else:
        # If backend is provided explicitly, try to load its config from project.yaml
        try:
            _, all_backends = load_agent_config()
            backend_config = all_backends.get(backend_name, {})
        except (FileNotFoundError, KeyError):
            backend_config = {}
    
    # Get the backend and execute
    print(f"🚀 Executing with backend: {backend_name}")
    backend = get_agent_backend(backend_name, backend_config)
    prompt = "Generate today's AI digest from all sources" if use_real_sources else "Use stub data"
    
    return backend.forward(prompt, use_real_sources=use_real_sources)

