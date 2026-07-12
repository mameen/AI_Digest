# Risks

1. Source instability (feeds change or break).
2. Hallucinated summaries if generation is unconstrained.
3. Duplicate news across many outlets.
4. Prompt injection in fetched content.
5. Over-scoping before a stable MVP exists.

## Mitigations

- keep deterministic validation
- keep source metadata
- constrain tool outputs
- fail closed when validation fails
