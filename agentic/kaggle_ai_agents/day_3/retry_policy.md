# Retry Policy

1. Source fetch retries: 2 with exponential backoff.
2. Parse retries: 1 after fallback parser.
3. Validation retries: 0 (fail fast, inspect cause).
4. Rendering retries: 1 if file write race occurs.
