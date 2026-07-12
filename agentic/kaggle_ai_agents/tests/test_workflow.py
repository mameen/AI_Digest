from kaggle_ai_agents.workflow import run_daily_brief, run_daily_brief_with_agent


def test_run_daily_brief_has_cards() -> None:
    brief = run_daily_brief()
    assert brief.cards


def test_run_daily_brief_cards_are_ranked_and_unique() -> None:
    brief = run_daily_brief()
    ranks = [card.rank for card in brief.cards]
    titles = [card.title for card in brief.cards]
    assert ranks == list(range(1, len(brief.cards) + 1))
    assert len(set(titles)) == len(titles)


def test_run_daily_brief_with_agent_has_cards() -> None:
    """Test that agent-driven workflow produces valid brief."""
    brief = run_daily_brief_with_agent(use_real_sources=False)
    assert brief.cards
    assert len(brief.cards) > 0


def test_run_daily_brief_with_agent_cards_ranked() -> None:
    """Test that agent-produced cards maintain ranking order."""
    brief = run_daily_brief_with_agent(use_real_sources=False)
    ranks = [card.rank for card in brief.cards]
    assert ranks == list(range(1, len(brief.cards) + 1))


def test_run_daily_brief_with_agent_cards_unique() -> None:
    """Test that agent-produced cards are deduplicated."""
    brief = run_daily_brief_with_agent(use_real_sources=False)
    titles = [card.title for card in brief.cards]
    assert len(set(titles)) == len(titles)
