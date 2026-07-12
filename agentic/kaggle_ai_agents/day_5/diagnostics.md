# Diagnostics

Generate one diagnostic artifact per run with:

- run_id
- stage durations
- source failures
- validation errors
- output file paths

Mirror production-style artifact family where practical:

1. `<prefix>.diagnostics.json`
2. `<prefix>.diagnostics.html`
3. `<prefix>.run.log`

This keeps comparison straightforward against `app/diagnostics/` reference outputs.
