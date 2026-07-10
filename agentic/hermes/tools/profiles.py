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

# Canonical GO lifecycle for Concierge STATUS — kanban workers are only the middle.
GO_PIPELINE_PROCESS: tuple[dict[str, str], ...] = (
    {
        "id": "kick",
        "label": "Kick GO",
        "actor": "Concierge digest_go → manage.py go subprocess",
        "kanban": "no",
        "deliverable": "kanban graph + run prefix",
    },
    {
        "id": "ingest",
        "label": "Ingest warm-up",
        "actor": "manage.py go (deterministic)",
        "kanban": "no",
        "deliverable": ".cache/<prefix>/ preflight + crawl + structured",
    },
    {
        "id": "research",
        "label": "Research × N",
        "actor": "orio_researcher kanban workers",
        "kanban": "yes",
        "deliverable": "output.md per task (+ .runtime/artifacts/<prefix>/research/)",
    },
    {
        "id": "librarian",
        "label": "Librarian fan-in",
        "actor": "orio_librarian kanban worker",
        "kanban": "yes",
        "deliverable": "librarian.md (+ .runtime/artifacts/<prefix>/librarian.md)",
    },
    {
        "id": "synthesizer",
        "label": "Synthesizer JSON",
        "actor": "orio_synthesizer kanban worker (synthesize_digest tool only)",
        "kanban": "yes",
        "deliverable": "digest.json in workspace (persisted under .runtime/artifacts/<prefix>/)",
    },
    {
        "id": "render",
        "label": "Ground · validate · render",
        "actor": "manage.py go Phase C — render-from-board (not an agent, not pipeline/render.py CLI)",
        "kanban": "no",
        "deliverable": "agentic/hermes/reports/<prefix>.html + .json",
    },
    {
        "id": "handover",
        "label": "Handover + board cleanup",
        "actor": "manage.py go (end of subprocess)",
        "kanban": "no",
        "deliverable": ".runtime/artifacts/<prefix>/handover.json; digest tasks archived",
    },
    {
        "id": "assess",
        "label": "Assess · deploy · publish",
        "actor": "Concierge digest_assess_run / digest_deploy_app / digest_publish",
        "kanban": "no",
        "deliverable": "app/reports/<prefix>.html after deploy (human-gated push)",
    },
)

PHASE_GUIDE: dict[str, str] = {
    "idle": "No digest kanban tasks — last report prefix may still exist under agentic/hermes/reports/.",
    "research": "Research workers running or pending — check per-task output.md gates.",
    "librarian": "Librarian merge running or pending — needs all research gates passed.",
    "synthesizer": "Synthesizer running or pending — reads librarian.md, writes digest.json via synthesize_digest.",
    "blocked": "Kanban marked done but artifact gate failed — NOT ready for render. Re-dispatch failed role (digest_go --prefix, no --fresh) or inspect gate errors.",
    "render": "All worker gates passed — GO subprocess should run Phase C (validate + render) or report may be missing if GO exited early.",
    "complete": "Report HTML exists for run prefix — run digest_assess_run before deploy/publish.",
}

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
