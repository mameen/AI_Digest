"""Deprecated module name — use ``llm_pipeline.local_server``."""

from llm_pipeline.local_server import DEFAULT_PORT, serve_local

serve = serve_local

__all__ = ["DEFAULT_PORT", "serve", "serve_local"]
