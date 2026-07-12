"""ADK-style agent orchestrating skills (source_discovery, dedupe_and_rank, validation).

This implements the course's recommendation for single-agent + skills-driven architecture.
The agent uses tool definitions similar to google.adk.agents.Agent and orchestrates
the existing skills via subprocess calls.

Architecture:
    Agent (instruction-driven)
    ├─ Tool 1: discover_news (source_discovery skill)
    ├─ Tool 2: rank_stories (dedupe_and_rank skill)
    └─ Tool 3: validate_brief (artifact_validation skill)
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

from kaggle_ai_agents.models import DailyBrief, NewsItem


class ADKAgent:
    """Single-agent orchestrator using ADK patterns."""
    
    def __init__(
        self,
        name: str = "ai_digest",
        instruction: str = "",
        tools: list[dict] | None = None,
        use_real_sources: bool = True,
    ):
        """Initialize agent with instruction and tool definitions.
        
        Args:
            name: Agent name
            instruction: System instruction for the agent
            tools: Custom tool definitions (auto-generated if None)
            use_real_sources: If True, fetch from real sources; else use stubs
        """
        self.name = name
        self.instruction = instruction
        self.tools = tools or []
        self.use_real_sources = use_real_sources
        
        # Auto-register standard skills
        if not self.tools:
            self._register_default_tools()
    
    def _register_default_tools(self) -> None:
        """Register the three core skills as tools."""
        self.tools = [
            {
                "name": "discover_news",
                "description": "Discover news items from configured sources (RSS, YouTube, web scrape, APIs)",
                "parameters": {
                    "sources": {"type": "list", "description": "Optional source IDs to fetch from"},
                    "limit": {"type": "int", "description": "Max items per source (default 10)"},
                },
                "handler": self._tool_discover_news,
            },
            {
                "name": "rank_stories",
                "description": "Deduplicate and rank stories by relevance",
                "parameters": {
                    "items": {"type": "list", "description": "NewsItem records to rank"},
                    "limit": {"type": "int", "description": "Return top N (default 10)"},
                },
                "handler": self._tool_rank_stories,
            },
            {
                "name": "validate_brief",
                "description": "Validate a DailyBrief artifact against schema",
                "parameters": {
                    "brief": {"type": "dict", "description": "Brief JSON object"},
                },
                "handler": self._tool_validate_brief,
            },
        ]
    
    def forward(self, user_prompt: str) -> DailyBrief:
        """Run agent with user prompt.
        
        This demonstrates the orchestration loop:
        1. Parse user intent
        2. Decide which tools to call
        3. Execute tools in sequence
        4. Validate result
        5. Return brief
        
        For MVP: Use deterministic orchestration (call all tools in order).
        Future: Can integrate LLM reasoning here.
        """
        print(f"Agent '{self.name}' received prompt: {user_prompt}")
        
        # Phase 1: Discover news
        print("→ Phase 1: Discovering news from sources...")
        discovered = self._tool_discover_news(use_real_sources=self.use_real_sources)
        print(f"  Found {len(discovered)} items")
        
        # Phase 2: Rank and deduplicate
        print("→ Phase 2: Ranking and deduplicating...")
        ranked = self._tool_rank_stories(discovered, limit=10)
        print(f"  Selected top {len(ranked)} stories")
        
        # Phase 3: Create brief and validate
        print("→ Phase 3: Creating and validating brief...")
        cards = [
            {
                "rank": i + 1,
                "title": item["title"],
                "url": item["url"],
                "why_it_matters": item.get("summary", ""),
            }
            for i, item in enumerate(ranked)
        ]
        
        brief_dict = {
            "date": str(date.today()),
            "theme": "AI signal over noise",
            "cards": cards,
        }
        
        # Validate
        is_valid = self._tool_validate_brief(brief_dict)
        if not is_valid:
            raise ValueError("Generated brief failed schema validation")
        
        print("  ✅ Brief schema valid")
        
        # Convert to typed model
        return DailyBrief.model_validate(brief_dict)
    
    def _tool_discover_news(self, sources: list[str] | None = None, limit: int = 10, use_real_sources: bool = True) -> list[dict]:
        """Tool: Discover news items from configured sources (via source_discovery skill).
        
        Args:
            sources: Optional list of source IDs to fetch from
            limit: Max items per source
            use_real_sources: If True, fetch from real sources; else use stubs
        """
        # Use stubs if not using real sources
        if not use_real_sources:
            from kaggle_ai_agents.tools.news_sources import fetch_contract_stub_items
            items = fetch_contract_stub_items()
            return [
                {
                    "source_id": item.source_id,
                    "title": item.title,
                    "url": str(item.url),
                    "summary": item.summary,
                }
                for item in items
            ]
        
        try:
            # Find repo root by walking up from this file until we find run_tests.py
            current = Path(__file__)
            repo_root = None
            for parent in current.parents:
                if (parent / "run_tests.py").exists():
                    repo_root = parent
                    break
            
            if not repo_root:
                raise FileNotFoundError("Could not find repo root (run_tests.py)")
            
            skills_dir = repo_root / "agentic" / "kaggle_ai_agents" / "skills"
            script = skills_dir / "source_discovery" / "scripts" / "discover.py"
            config = repo_root / "agentic" / "kaggle_ai_agents" / "config" / "project.yaml"
            
            cmd = [
                sys.executable,
                str(script),
                "--config", str(config),
            ]
            
            # Optional: filter by specific sources
            if sources:
                cmd.extend(["--sources"] + sources)
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                print(f"  ⚠️  Discovery error: {result.stderr[:200]}")
                return []
            
            # Parse JSON output
            items = json.loads(result.stdout)
            return items[:limit * len(sources or [1])]  # Respect limit
        
        except Exception as e:
            print(f"  ⚠️  Discovery failed: {e}")
            return []
    
    def _tool_rank_stories(self, items: list[dict] | list[NewsItem], limit: int = 10) -> list[dict]:
        """Tool: Rank and deduplicate stories (via dedupe_and_rank skill)."""
        try:
            # Convert NewsItem to dict if needed
            if items and isinstance(items[0], NewsItem):
                items = [
                    {
                        "source_id": i.source_id,
                        "title": i.title,
                        "url": str(i.url),
                        "summary": i.summary,
                    }
                    for i in items
                ]
            
            # Write to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(items, f)
                temp_file = f.name
            
            # Call rank script
            current = Path(__file__)
            repo_root = None
            for parent in current.parents:
                if (parent / "run_tests.py").exists():
                    repo_root = parent
                    break
            
            if not repo_root:
                raise FileNotFoundError("Could not find repo root")
            
            skills_dir = repo_root / "agentic" / "kaggle_ai_agents" / "skills"
            script = skills_dir / "dedupe_and_rank" / "scripts" / "rank.py"
            
            result = subprocess.run(
                [sys.executable, str(script), temp_file, "--limit", str(limit)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            # Clean up
            Path(temp_file).unlink()
            
            if result.returncode != 0:
                print(f"  ⚠️  Ranking error: {result.stderr[:200]}")
                return items[:limit]
            
            return json.loads(result.stdout)
        
        except Exception as e:
            print(f"  ⚠️  Ranking failed: {e}")
            return items[:limit]
    
    def _tool_validate_brief(self, brief: dict | DailyBrief) -> bool:
        """Tool: Validate brief against schema (via artifact_validation skill)."""
        try:
            # Convert to dict if needed
            if isinstance(brief, DailyBrief):
                brief = brief.model_dump()
            
            # Write to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(brief, f)
                temp_file = f.name
            
            # Call validate script
            current = Path(__file__)
            repo_root = None
            for parent in current.parents:
                if (parent / "run_tests.py").exists():
                    repo_root = parent
                    break
            
            if not repo_root:
                raise FileNotFoundError("Could not find repo root")
            
            skills_dir = repo_root / "agentic" / "kaggle_ai_agents" / "skills"
            script = skills_dir / "artifact_validation" / "scripts" / "validate.py"
            
            result = subprocess.run(
                [sys.executable, str(script), temp_file],
                capture_output=True,
                text=True,
                timeout=5,
            )
            
            # Clean up
            Path(temp_file).unlink()
            
            return result.returncode == 0
        
        except Exception as e:
            print(f"  ⚠️  Validation error: {e}")
            return False


def create_agent(
    name: str = "ai_digest",
    instruction: str | None = None,
    use_real_sources: bool = True,
) -> ADKAgent:
    """Factory function to create an agent with sensible defaults.
    
    This follows the ADK pattern of:
        agent = create_agent(
            name="my_agent",
            instruction="You are a news curator...",
            use_real_sources=False  # For testing
        )
        brief = agent.forward("Generate today's digest")
    
    Args:
        name: Agent name
        instruction: System instruction (auto-generated if None)
        use_real_sources: If True, fetch from real sources; else use stubs
    
    Returns:
        ADKAgent: Initialized agent ready to run
    """
    default_instruction = (
        "You are an AI news curator. Your job is to find the latest and most important "
        "AI/ML stories from configured sources. Discover news, rank by relevance, and "
        "produce a curated 10-card brief explaining why each story matters."
    )
    
    return ADKAgent(
        name=name,
        instruction=instruction or default_instruction,
        use_real_sources=use_real_sources,
    )
