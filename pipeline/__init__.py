"""AI Digest pipeline stages."""

# Release line of the generator (MAJOR.MINOR). Bump deliberately:
# major = breaking pipeline/schema change, minor = new feature/source.
__version__ = "0.4"


def generator_version(prefix: str) -> str:
    """Human-readable version: release line + run prefix as the third segment.

    e.g. ``generator_version("20260630120000") -> "0.4.20260630120000"``,
    read as "code v0.4 produced the 20260630120000 report".
    """
    return f"{__version__}.{prefix}" if prefix else __version__
