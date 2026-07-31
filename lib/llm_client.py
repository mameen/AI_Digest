"""Stub: re-export from llm_pipeline.llm_client until T2 extracts to lib/llm_client.py."""

from llm_pipeline.llm_client import make_client, make_raw_chat  # type: ignore[import-untyped]

__all__ = ["make_client", "make_raw_chat"]
