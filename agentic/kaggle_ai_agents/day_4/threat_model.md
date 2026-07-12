# Threat Model

## Threats

1. Prompt injection in fetched pages.
2. Malicious or malformed feed payloads.
3. Leaked secrets in logs or artifacts.
4. Broken links that weaken trust.

## Trust Boundaries

- external sources are untrusted
- local config is trusted after validation
- publish step requires validated artifacts only
