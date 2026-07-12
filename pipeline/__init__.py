"""DEPRECATED compatibility package for ``llm_pipeline``; do not add new imports from ``pipeline``."""
from llm_pipeline import __version__, generator_version
__all__ = ["__version__", "generator_version"]
