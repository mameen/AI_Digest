"""Tests for the ADK agent implementation."""

from __future__ import annotations

import pytest

from kaggle_ai_agents.adk_agent import ADKAgent, create_agent
from kaggle_ai_agents.models import DailyBrief


def test_create_agent_returns_agent() -> None:
    """Test that create_agent factory works."""
    agent = create_agent(name="test_agent")
    assert agent is not None
    assert agent.name == "test_agent"


def test_agent_has_tools() -> None:
    """Test that agent registers default tools."""
    agent = create_agent()
    assert len(agent.tools) >= 3
    tool_names = {t["name"] for t in agent.tools}
    assert "discover_news" in tool_names
    assert "rank_stories" in tool_names
    assert "validate_brief" in tool_names


def test_agent_forward_returns_daily_brief() -> None:
    """Test that agent.forward() produces a valid brief."""
    agent = create_agent()
    brief = agent.forward("Generate today's digest")
    
    assert isinstance(brief, DailyBrief)
    assert brief.date is not None
    assert brief.theme is not None
    assert len(brief.cards) > 0
    assert len(brief.cards) <= 10


def test_agent_brief_cards_have_required_fields() -> None:
    """Test that brief cards from agent have all required fields."""
    agent = create_agent()
    brief = agent.forward("Generate digest")
    
    for card in brief.cards:
        assert card.rank >= 1
        assert card.title is not None
        assert len(card.title) > 0
        assert card.url is not None
        assert card.why_it_matters is not None


def test_agent_instruction_is_used() -> None:
    """Test that custom instruction is stored."""
    custom_instruction = "Be very selective about stories"
    agent = create_agent(instruction=custom_instruction)
    
    assert agent.instruction == custom_instruction


def test_agent_with_default_instruction() -> None:
    """Test that agent uses sensible default instruction."""
    agent = create_agent()
    
    assert agent.instruction is not None
    assert "news curator" in agent.instruction.lower()
    assert "AI" in agent.instruction or "ai" in agent.instruction


def test_adk_agent_direct_instantiation() -> None:
    """Test that ADKAgent can be instantiated directly."""
    agent = ADKAgent(
        name="direct_agent",
        instruction="Direct instruction",
        tools=[],
    )
    
    assert agent.name == "direct_agent"
    assert agent.instruction == "Direct instruction"


def test_agent_tool_discover_news_handles_errors() -> None:
    """Test that discover_news tool handles errors gracefully."""
    agent = create_agent()
    
    # Call with invalid config should return empty list, not crash
    items = agent._tool_discover_news(sources=["nonexistent-source"])
    assert isinstance(items, list)


def test_agent_tool_rank_stories_returns_dict_list() -> None:
    """Test that rank_stories returns list of dicts."""
    agent = create_agent()
    
    test_items = [
        {"source_id": "test", "title": "Story 1", "url": "https://example.com/1", "summary": "Summary 1"},
        {"source_id": "test", "title": "Story 2", "url": "https://example.com/2", "summary": "Summary 2"},
    ]
    
    ranked = agent._tool_rank_stories(test_items, limit=2)
    
    assert isinstance(ranked, list)
    assert all(isinstance(item, dict) for item in ranked)
    assert len(ranked) <= 2


def test_agent_tool_validate_brief_with_valid_brief() -> None:
    """Test that validate_brief recognizes valid briefs."""
    agent = create_agent()
    
    valid_brief = {
        "date": "2026-07-12",
        "theme": "Test theme",
        "cards": [
            {
                "rank": 1,
                "title": "Story",
                "url": "https://example.com",
                "why_it_matters": "Important",
            }
        ],
    }
    
    is_valid = agent._tool_validate_brief(valid_brief)
    assert is_valid is True


def test_agent_tool_validate_brief_with_invalid_brief() -> None:
    """Test that validate_brief rejects invalid briefs."""
    agent = create_agent()
    
    invalid_brief = {
        "date": "invalid",
        # Missing theme
        # Missing cards
    }
    
    is_valid = agent._tool_validate_brief(invalid_brief)
    assert is_valid is False


def test_agent_forward_deterministic_with_stub_data() -> None:
    """Test that agent produces consistent output (deterministic)."""
    agent1 = create_agent()
    agent2 = create_agent()
    
    # Both agents should produce briefs with same structure
    brief1 = agent1.forward("Test")
    brief2 = agent2.forward("Test")
    
    assert len(brief1.cards) > 0
    assert len(brief2.cards) > 0
    assert brief1.theme == brief2.theme
