"""
Shared cache helpers for digest scripts.

Cache files live in PROJECT/.cache/ and follow the naming convention:
    YYYYMMDDHHMMSS_<script_name>.json

Example:
    .cache/20260515120000_fetch_youtube.json
    .cache/20260515120000_fetch_typography.json
    .cache/20260515120000_fetch_research.json

Scripts write here so preflight.py (and Claude) can read them back without
re-fetching.  The .cache/ folder is gitignored.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[3]
CACHE_DIR = PROJECT_DIR / ".cache"


def cache_path(prefix: str, script_name: str) -> Path:
    """
    Return the canonical .cache path for a given prefix + script.

    >>> cache_path("20260515120000", "fetch_youtube")
    PosixPath('.../AIDigest/.cache/20260515120000_fetch_youtube.json')
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{prefix}_{script_name}.json"


def cache_write(data: dict | list, prefix: str, script_name: str) -> Path:
    """Serialise *data* to the cache file and return its path."""
    path = cache_path(prefix, script_name)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  💾  cached → {path.relative_to(PROJECT_DIR)}", file=sys.stderr)
    return path


def cache_read(prefix: str, script_name: str) -> dict | list | None:
    """
    Read an existing cache file.  Returns None (not an error) if absent.
    Dies loudly if the file exists but is unreadable or invalid JSON.
    """
    path = cache_path(prefix, script_name)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        print(f"  📂  cache hit → {path.relative_to(PROJECT_DIR)}", file=sys.stderr)
        return data
    except json.JSONDecodeError as e:
        _die(f"Cache file is corrupt (invalid JSON): {path}\n    {e}")


def cache_stale(prefix: str, script_name: str, max_age_hours: float = 12) -> bool:
    """
    Return True if the cache file is missing OR older than *max_age_hours*.
    Useful for deciding whether to re-fetch.
    """
    path = cache_path(prefix, script_name)
    if not path.exists():
        return True
    age = (datetime.now(timezone.utc).timestamp() - path.stat().st_mtime) / 3600
    return age > max_age_hours


def build_prefix(dt: datetime | None = None) -> str:
    """Return a 14-digit timestamp prefix for today's digest (noon UTC)."""
    if dt is None:
        dt = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    return dt.strftime("%Y%m%d%H%M%S")


def list_cache(prefix: str | None = None) -> list[Path]:
    """List all cache files, optionally filtered by prefix."""
    if not CACHE_DIR.exists():
        return []
    files = sorted(CACHE_DIR.glob("*.json"))
    if prefix:
        files = [f for f in files if f.name.startswith(prefix)]
    return files


def _die(msg: str) -> None:
    print(f"\n❌  CACHE ERROR: {msg}", file=sys.stderr)
    sys.exit(1)
