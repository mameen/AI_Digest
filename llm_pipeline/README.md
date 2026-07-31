# LLM Pipeline POC

The LLM Pipeline is the stable staged baseline for AI Digest.

It runs a deterministic flow:

```text
ingest -> enrich -> validate -> render
```

The pipeline proves that the digest can be generated, grounded, validated, and
rendered without multi-agent orchestration. It is the simplest runnable POC in
the repo.

## Run

```powershell
python run.py --start 2026-07-29 --history 10
python run_tests.py
```

## What It Contains

| Area | Files |
|---|---|
| Ingest | `fetch.py`, `leaderboards.py`, `structured_sources.py` |
| Enrich | `enrich.py`, `editorial.py`, `llm_client.py`, `tools.py` |
| Validate | `validate.py`, `grounding.py`, `schema.py` |
| Render | `render.py`, `diagnostics.py`, frame/nav/footer helpers |
| Admin | `admin_ops.py`, `local_server.py`, `doctor.py` |

## Outputs

Development outputs are written under [`reports/`](reports/) and
[`diagnostics/`](diagnostics/). Approved website artifacts are copied to
[`../app/`](../app/) and should be treated as the published source of truth.

## Relationship to Other POCs

| POC | Relationship |
|---|---|
| Hermes Multi-Agent | Reuses deterministic validation/rendering ideas while exploring role-based orchestration |
| Kaggle AI Agents | Standalone course sandbox that borrows the skills/tooling mindset |
| Single Agent + Skills | Future direction for reducing orchestration overhead while keeping deterministic boundaries |

The archive-facing overview lives in [`../README.md`](../README.md).
