# Hermes SOUL files (ORIO crew)

Source-of-truth persona files for AI Digest Hermes profiles. Deployed by
`manage.py setup` into each profile's `SOUL.md`.

| File | Profile | Display name | Purpose |
|---|---|---|---|
| `orio_concierge.md` | `orio_concierge` | Concierge | Intent routing, GO/STATUS, kanban orchestration |
| `orio_researcher.md` | `orio_researcher` | Researcher | Per-task fetch/summarize; kanban worker protocol |
| `orio_librarian.md` | `orio_librarian` | Librarian | Merge researcher artifacts; taxonomy + graph |
| `orio_synthesizer.md` | `orio_synthesizer` | Synthesizer | Final digest JSON from librarian output |

**ORIO** — *Open Research Intelligence Observatory* — internal codename for the
AI Digest agent crew (mascot: Oreo, the tuxedo cat beside Hermes in `docs/AI_Digest.png`).
