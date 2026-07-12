"""DEPRECATED compatibility shim -> ``llm_pipeline``; do not add new imports from ``pipeline``."""
import importlib as _il
import sys as _s
_m = _il.import_module("llm_pipeline.visualize")
_s.modules[__name__] = _m
