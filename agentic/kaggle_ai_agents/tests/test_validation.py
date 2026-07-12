from kaggle_ai_agents.validation.schemas import validate_brief


def test_validate_brief_minimal_shape() -> None:
    brief = validate_brief(
        {
            "date": "2026-07-11",
            "theme": "AI signal",
            "cards": [
                {
                    "rank": 1,
                    "title": "Test",
                    "url": "https://example.com/a",
                    "why_it_matters": "Important",
                }
            ],
        }
    )
    assert brief.cards[0].rank == 1
