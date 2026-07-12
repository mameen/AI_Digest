from kaggle_ai_agents.workflow import run_daily_brief


def test_run_daily_brief_has_cards() -> None:
    brief = run_daily_brief()
    assert brief.cards
