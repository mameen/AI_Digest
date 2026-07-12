"""Source adapters: config-driven source registry and normalization helpers.

Real sources are defined in config/project.yaml.  The fetch_stub_* helpers
below are *test fixtures only* — they are not the real source list.
"""

from __future__ import annotations

import json
import subprocess
import sys
import yaml
from pathlib import Path

from kaggle_ai_agents.models import NewsItem


# ── Config-driven source registry ─────────────────────────────────────────────

def load_source_registry(config_path: str | Path | None = None) -> list[dict]:
    """Load the full source list from config/project.yaml."""
    if config_path is None:
        # tools/news_sources.py is 5 levels below kaggle_ai_agents root
        config_path = Path(__file__).parents[3] / "config" / "project.yaml"
    path = Path(config_path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload.get("sources", [])


def sources_by_kind(kind: str, config_path: str | Path | None = None) -> list[dict]:
    """Return all source entries matching a given kind (rss, web_scrape, etc.)."""
    return [s for s in load_source_registry(config_path) if s.get("kind") == kind]


# ── Normalization ──────────────────────────────────────────────────────────────

def normalize_source_records(records: list[dict[str, str]]) -> list[NewsItem]:
    """Map heterogeneous fetch records into the shared NewsItem schema."""
    normalized: list[NewsItem] = []
    for record in records:
        title = record.get("title") or record.get("headline") or ""
        url = record.get("url") or record.get("source_url") or "https://example.com"
        summary = record.get("summary") or record.get("raw_excerpt") or ""
        normalized.append(
            NewsItem(
                source_id=record.get("source_id", "unknown"),
                title=title,
                url=url,
                summary=summary,
            )
        )
    return normalized


# ── Discover items via source_discovery skill ──────────────────────────────────

def discover_items(config_path: str | Path | None = None) -> list[NewsItem]:
    """Fetch items from all configured sources using the source_discovery skill.
    
    This calls scripts/discover.py which orchestrates all source adapters
    and applies security filtering.
    
    Args:
        config_path: Optional path to config/project.yaml (defaults to repo config)
        
    Returns:
        List of NewsItem objects (clean, filtered)
        
    Raises:
        RuntimeError: if discover.py exits with non-zero code
    """
    if config_path is None:
        # tools/news_sources.py is 5 levels below kaggle_ai_agents root
        config_path = Path(__file__).parents[3] / "config" / "project.yaml"
    
    discover_script = Path(__file__).parents[3] / "skills" / "source_discovery" / "scripts" / "discover.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(discover_script), "--config", str(config_path)],
            capture_output=True,
            text=True,
            check=False,  # Don't raise on non-zero exit
            timeout=30,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"discover.py failed: {result.stderr}")
        
        # Parse JSON output
        items_data = json.loads(result.stdout)
        
        # Convert to NewsItem objects
        items: list[NewsItem] = []
        for item_dict in items_data:
            items.append(NewsItem(
                source_id=item_dict.get("source_id", ""),
                title=item_dict.get("title", ""),
                url=item_dict.get("url", "https://example.com"),
                summary=item_dict.get("summary", ""),
            ))
        
        return items
    
    except json.JSONDecodeError as e:
        raise RuntimeError(f"discover.py returned invalid JSON: {e}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("discover.py timed out (>30s)")
    except Exception as e:
        raise RuntimeError(f"discover.py execution failed: {e}")


# ── Test fixtures (not real sources) ──────────────────────────────────────────

def _stub_source_records() -> list[dict[str, str]]:
    """Minimal heterogeneous records for unit tests — not the real source list."""
    return [
        {
            "source_id": "open-model-feed",
            "source_kind": "rss",
            "source_url": "https://example.com/open-model-benchmarks",
            "title": "Open model benchmarks improve",
            "summary": "New results show quality gains with lower latency.",
        },
        {
            "source_id": "interop-feed",
            "source_kind": "web",
            "source_url": "https://example.com/agent-tooling-standards",
            "headline": "Agent tooling standards emerging",
            "raw_excerpt": "Interoperability efforts reduce integration friction.",
        },
        {
            "source_id": "duplicate-host",
            "source_kind": "web",
            "source_url": "https://example.com/open-model-benchmarks?ref=dup",
            "title": "Open model benchmarks improve",
            "summary": "Duplicate candidate from another source.",
        },
    ]


def fetch_stub_items() -> list[NewsItem]:
    """Test fixture helper — returns normalized stub items for unit tests."""
    return normalize_source_records(_stub_source_records())


def fetch_contract_stub_items() -> list[NewsItem]:
    """Test fixture alias used in workflow tests."""
    return fetch_stub_items()
