"""Examples of using different agent backends.

This demonstrates how to call each backend and configure them.
"""

from kaggle_ai_agents.workflow import (
    run_daily_brief,
    run_daily_brief_with_agent,
    run_daily_brief_with_backend,
)


def example_direct_script():
    """Direct scripted orchestration (deterministic, fast for tests)."""
    print("\n=== Direct Script Backend ===")
    print("Best for: Testing, CI/CD, deterministic behavior")
    print("Speed: Fast (~30-60s with real sources)")
    
    brief = run_daily_brief(use_real_sources=False)
    print(f"Generated {len(brief.cards)} cards")
    for card in brief.cards[:3]:
        print(f"  • {card.title}")


def example_google_adk():
    """Google ADK-style agent orchestrator."""
    print("\n=== Google ADK Backend ===")
    print("Best for: Course requirements, instruction-driven, extensible")
    print("Speed: ~6-10min with real sources (includes YouTube discovery)")
    
    # Using legacy function
    brief = run_daily_brief_with_agent(use_real_sources=False)
    print(f"Generated {len(brief.cards)} cards")
    for card in brief.cards[:3]:
        print(f"  • {card.title}")


def example_ollama():
    """Local Ollama LLM-based agent (experimental)."""
    print("\n=== Ollama Backend (Experimental) ===")
    print("Best for: LLM-based ranking, local privacy, research")
    print("Requirements:")
    print("  1. Install Ollama: https://ollama.ai")
    print("  2. Start Ollama: ollama serve")
    print("  3. Pull model: ollama pull llama2")
    print("  4. Set backend in config/project.yaml to 'ollama'")
    print()
    
    try:
        brief = run_daily_brief_with_backend("ollama", use_real_sources=False)
        print(f"Generated {len(brief.cards)} cards (ranked by Ollama)")
        for card in brief.cards[:3]:
            print(f"  • {card.title}")
    except RuntimeError as e:
        print(f"⚠️  {e}")
        print("   Falling back to direct script backend...")
        brief = run_daily_brief_with_backend("direct_script", use_real_sources=False)
        print(f"Generated {len(brief.cards)} cards (script-ranked)")


def example_config_driven():
    """Config-driven backend selection (recommended for production)."""
    print("\n=== Config-Driven Backend ===")
    print("Best for: Production, easy backend switching")
    print("Configuration: config/project.yaml - agent.backend")
    
    # This loads backend from project.yaml automatically
    brief = run_daily_brief_with_backend(use_real_sources=False)
    print(f"Backend loaded from config")
    print(f"Generated {len(brief.cards)} cards")
    for card in brief.cards[:3]:
        print(f"  • {card.title}")


def example_override_backend():
    """Override config backend for a single run."""
    print("\n=== Backend Override ===")
    print("Even if config says 'ollama', can override to 'direct_script':")
    
    brief = run_daily_brief_with_backend(
        backend_name="direct_script",  # Override config
        use_real_sources=False
    )
    print(f"Generated {len(brief.cards)} cards (using direct_script)")


if __name__ == "__main__":
    print("Agent Backend Examples\n" + "=" * 60)
    
    example_direct_script()
    example_google_adk()
    example_config_driven()
    example_override_backend()
    
    # Note: Skip Ollama example unless specifically needed
    # example_ollama()
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("  • Fastest: direct_script (~30-60s stubs, ~2min real)")
    print("  • Course-aligned: google_adk (instruction-based)")
    print("  • LLM-based: ollama (requires local Ollama setup)")
    print("  • Production: use run_daily_brief_with_backend() with config")
