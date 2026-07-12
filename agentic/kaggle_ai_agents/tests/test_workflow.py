from kaggle_ai_agents.workflow import run_daily_brief


def test_run_daily_brief_has_cards() -> None:
    brief = run_daily_brief()
    assert brief.cards


def test_run_daily_brief_cards_are_ranked_and_unique() -> None:
    brief = run_daily_brief()
    ranks = [card.rank for card in brief.cards]
    titles = [card.title for card in brief.cards]
    assert ranks == list(range(1, len(brief.cards) + 1))
    assert len(set(titles)) == len(titles)
