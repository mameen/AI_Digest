"""AI Digest pipeline stages."""

# Semantic version of the generator (MAJOR.MINOR.PATCH). Bump deliberately:
# major = breaking pipeline/schema change, minor = new feature/source, patch = fix.
__version__ = "0.4.1"


def generator_version(prefix: str) -> str:
    """Human-readable build id: SemVer core + run prefix as build metadata.

    e.g. ``generator_version("20260630120000") -> "0.4.1+20260630120000"``,
    read as "code v0.4.1 produced the 20260630120000 report".
    """
    return f"{__version__}+{prefix}" if prefix else __version__
