"""Web helpers — thin re-export until llm_pipeline/tools.py moves here."""

from __future__ import annotations

from llm_pipeline.tools import verify_url, web_search

__all__ = ["verify_url", "web_search"]
