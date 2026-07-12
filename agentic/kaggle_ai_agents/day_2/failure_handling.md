# Failure Handling

1. Source timeout: log and continue with remaining sources.
2. Malformed response: mark source failed and continue.
3. Empty run: produce explicit "no stories" artifact with diagnostics.
4. Validation failure: stop publish step and write error report.
