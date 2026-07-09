"""AI Digest staged pipeline (LLM-enhanced, non-agentic).

Implementation lives in ``llm_pipeline``; ``pipeline`` is a backward-compatible shim.
"""

# Release line of the generator (MAJOR.MINOR). Bump deliberately:
# major = breaking pipeline/schema change, minor = new feature/source.
# 0.6: HW/network diagnostics, archive trend charts, dark/light themes.
__version__ = "0.6"


def generator_version(prefix: str) -> str:
    """Human-readable version: release line + run prefix as the third segment.

    e.g. ``generator_version("20260702120000") -> "0.5.20260702120000"``,
    read as "code v0.5 produced the 20260702120000 report".
    """
    return f"{__version__}.{prefix}" if prefix else __version__
