# Pipeline diagnostics (GitHub Pages)

Per-run telemetry: wall time, CPU time, LLM token usage, stage waterfall.

Open **`index.html`** for the diagnostics archive frame. Each run also has `{prefix}.diagnostics.json` and `{prefix}.diagnostics.html`.

Sample runs in `diagnostics/` used **qwen3.6:35b** on an RTX 4090. Dev default is **llama3.1:latest** (128K context; Hermes-compatible).
