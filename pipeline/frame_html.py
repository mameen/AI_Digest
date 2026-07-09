"""Backward-compatible import path — use ``llm_pipeline`` in new code."""
import importlib as _il
import sys as _s
_m = _il.import_module("llm_pipeline.frame_html")
_s.modules[__name__] = _m
