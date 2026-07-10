"""AI Digest profile constants and helpers — role normalization, display labels, graph."""

from __future__ import annotations

# Logical pipeline roles (artifact gates, orchestration comparisons).
RESEARCHER = "researcher"
LIBRARIAN = "librarian"
SYNTHESIZER = "synthesizer"
CONCIERGE = "concierge"

# Hermes profile names created by manage.py setup (kanban assignee + ~/.hermes/profiles).
HERMES_RESEARCHER = "orio_researcher"
HERMES_LIBRARIAN = "orio_librarian"
HERMES_SYNTHESIZER = "orio_synthesizer"
HERMES_CONCIERGE = "orio_concierge"

KANBAN_ASSIGNEE: dict[str, str] = {
    RESEARCHER: HERMES_RESEARCHER,
    LIBRARIAN: HERMES_LIBRARIAN,
    SYNTHESIZER: HERMES_SYNTHESIZER,
    CONCIERGE: HERMES_CONCIERGE,
}

# Worker graph descriptions
WORKER_GRAPH = "research × N → librarian → synthesizer → render"
PIPELINE_GRAPH = WORKER_GRAPH

# Display labels for human-readable output
DISPLAY: dict[str, str] = {
    RESEARCHER: "Researcher",
    LIBRARIAN: "Librarian",
    SYNTHESIZER: "Synthesizer",
    CONCIERGE: "Concierge",
    HERMES_RESEARCHER: "Researcher",
    HERMES_LIBRARIAN: "Librarian",
    HERMES_SYNTHESIZER: "Synthesizer",
    HERMES_CONCIERGE: "Concierge",
}

# Worker profiles used in the pipeline
WORKERS = frozenset([HERMES_RESEARCHER, HERMES_LIBRARIAN, HERMES_SYNTHESIZER])

# Legacy profile names that should map to current workers
LEGACY: dict[str, str] = {
    "ai_news_researcher": RESEARCHER,
    "ai_news_librarian": LIBRARIAN,
    "ai_news_synthesizer": SYNTHESIZER,
}

# Legacy Hermes profile dirs removed by manage.py setup (superseded by orio_*).
LEGACY_HERMES_PROFILES: frozenset[str] = frozenset(
    [
        "concierge",
        "researcher",
        "librarian",
        "synthesizer",
        "ai_news_concierge",
        "ai_news_researcher",
        "ai_news_librarian",
        "ai_news_synthesizer",
    ]
)

DEPRECATED_PROFILES = LEGACY_HERMES_PROFILES

# Logical roles for STATUS / orchestration summaries (not Hermes profile names).
LOGICAL_ROLES = (CONCIERGE, RESEARCHER, LIBRARIAN, SYNTHESIZER)

_ASSIGNEE_ALIASES: dict[str, str] = {
    RESEARCHER: RESEARCHER,
    LIBRARIAN: LIBRARIAN,
    SYNTHESIZER: SYNTHESIZER,
    CONCIERGE: CONCIERGE,
    HERMES_RESEARCHER: RESEARCHER,
    HERMES_LIBRARIAN: LIBRARIAN,
    HERMES_SYNTHESIZER: SYNTHESIZER,
    HERMES_CONCIERGE: CONCIERGE,
    **LEGACY,
}


def normalize(s: str) -> str:
    """Normalize an assignee string to a logical pipeline role."""
    return _ASSIGNEE_ALIASES.get(s.strip().lower(), s.strip().lower())


def kanban_assignee(role: str) -> str:
    """Hermes profile name for a logical pipeline role (kanban --assignee)."""
    key = normalize(role)
    try:
        return KANBAN_ASSIGNEE[key]
    except KeyError as exc:
        raise ValueError(f"unknown pipeline role: {role!r}") from exc
