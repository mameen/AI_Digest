# Principles & Local Workflow

Read this first. These are the non-negotiable rules of engagement for the
project. They exist because this is a **showcase** repo — the code and its
process are both on display.

## The five principles

### 1. Showcase-grade engineering
Hold a high standard of engineering excellence, accuracy, consistency, and
discipline. Every change should read as if it will be reviewed by a hiring
committee, because it might be. No sloppy commits, no half-measures, no
"temporary" hacks left in `main`.

### 2. Keep it simple — but weigh the options
Prefer the simplest design that works. *Before* committing to any non-trivial
approach, enumerate **at least three valid options**, note the trade-offs, and
record why the chosen one won. Simplicity is a decision you justify, not a
default you fall into.

### 3. Execute a proper local workflow
For every meaningful change, in order:

1. **Describe the change** — state intent and scope before editing.
2. **Lint** — keep the tree clean; fix warnings you introduce.
3. **Test** — `python run_tests.py` must be green (Python + Node), with a
   fixture-backed test covering the change.
4. **Version** — the build segment `YYYYMMDDHHmmss` (the run prefix) is the third
   segment and moves automatically each run. **MAJOR.MINOR is bumped only with
   explicit maintainer approval** — never bump the release line on your own.
   Format: `MAJOR.MINOR.<build:YYYYMMDDHHmmss>` (e.g. `0.5.20260702120000`).
5. **Commit on a dedicated branch** — descriptive message, logical grouping.
   `main` is protected and always shippable. **Never push without explicit
   permission.**

### 4. Honest, true, accurate, auditable data
The digest's credibility is the product. Every story must be real and every link
verifiable. Never ship a fabricated URL — the grounding guard demotes what it
can't verify. Every story is **traceable** via a deterministic `provenance`
token (JSON) surfaced as a clickable trace in the UI. Provenance is pipeline
metadata, never authored by the LLM.

### 5. Self-check and reflect on results
Green tests are necessary, not sufficient. After a change: regenerate the
affected artifact, confirm it is **not degraded** (story count and per-category
coverage hold), and reason explicitly about whether the original goal was met.
The grounding guard is the pipeline's built-in reflection pass; you are the
outer one.

## Versioning, precisely

- **Source of truth:** `__version__` in `pipeline/__init__.py` — the release line
  `MAJOR.MINOR` only.
- **MAJOR** = breaking pipeline/schema change. **MINOR** = new feature/source.
  Both require maintainer sign-off.
- **Build segment** = the run prefix, appended by `generator_version(prefix)`.
  Reports are traced by this, never re-stamped to the current line.
- Surface it as `generator_version` in the report JSON; footers show the bare
  release line `v<MAJOR.MINOR>`.

## Testing philosophy (see `.agents/AGENTS.md` for the full policy)

- **Test the real thing. Avoid mocks.** Exercise production code against committed
  fixtures under `tests/data/`.
- Python pipeline → `unittest`; browser widget pure logic → `node --test` via the
  `module.exports` guard. One command runs both: `python run_tests.py`.
- When you change a parser, the widget, the schema, or a source, add/extend a
  fixture-backed test rather than asserting against hand-written strings.

## Post-change checklist (the loop, no shortcuts)

1. Regenerate the affected report/artifact; confirm it is **not** degraded.
2. `python run_tests.py` green (Python + Node).
3. Commit on a topic branch (`feat/…`, `fix/…`, `chore/…`), never `main`.
4. **Ask permission before pushing.** State exactly what will be pushed and wait
   for an explicit yes.

## Scope discipline

Do what was asked — nothing more, nothing less. Don't create files (especially
docs) unless they're necessary or explicitly requested. Prefer editing an
existing file over adding a new one. For anything potentially damaging
(committing, pushing, merging, deploying, installing deps), get explicit
permission first.
