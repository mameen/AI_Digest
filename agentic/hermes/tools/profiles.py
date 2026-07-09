"""ORIO Hermes profile names — scoped ``orio_*`` roles (AI Digest crew)."""

from __future__ import annotations

CONCIERGE = "orio_concierge"
RESEARCHER = "orio_researcher"
LIBRARIAN = "orio_librarian"
SYNTHESIZER = "orio_synthesizer"

ALL = (CONCIERGE, RESEARCHER, LIBRARIAN, SYNTHESIZER)
WORKERS = (RESEARCHER, LIBRARIAN, SYNTHESIZER)

LEGACY = {
    "concierge": CONCIERGE,
    "researcher": RESEARCHER,
    "librarian": LIBRARIAN,
    "synthesizer": SYNTHESIZER,
    "ai_news_concierge": CONCIERGE,
    "ai_news_researcher": RESEARCHER,
    "ai_news_librarian": LIBRARIAN,
    "ai_news_synthesizer": SYNTHESIZER,
}

DEPRECATED_PROFILES = (
    "concierge",
    "researcher",
    "librarian",
    "synthesizer",
    "ai_news_concierge",
    "ai_news_researcher",
    "ai_news_librarian",
    "ai_news_synthesizer",
)

DISPLAY = {
    CONCIERGE: "Concierge",
    RESEARCHER: "Researcher",
    LIBRARIAN: "Librarian",
    SYNTHESIZER: "Synthesizer",
}

PIPELINE_GRAPH = (
    f"{CONCIERGE} → {RESEARCHER} × N → {LIBRARIAN} → {SYNTHESIZER} → render"
)
WORKER_GRAPH = f"{RESEARCHER} × N → {LIBRARIAN} → {SYNTHESIZER} → render"


def is_worker(assignee: str) -> bool:
    key = (assignee or "").lower()
    return key in WORKERS or key in {k for k, v in LEGACY.items() if v in WORKERS}


def normalize(assignee: str) -> str:
    key = (assignee or "").lower()
    return LEGACY.get(key, key)
