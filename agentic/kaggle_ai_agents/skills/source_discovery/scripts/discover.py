#!/usr/bin/env python3
"""Source discovery script: fetch items from configured sources and apply security gate.

Usage:
    python discover.py --config <config.yaml> [--sources source_id1 source_id2 ...]

Input:
    - config.yaml: project config with sources list
    - --sources: optional filter to fetch only specific sources by id

Output:
    - JSON array of {source_id, title, url, summary} items to stdout
    - Security-gated (dangerous content blocked)

Exit code:
    0: success
    1: error (missing config, fetch failure, etc.)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add src/ to path so we can import kaggle_ai_agents
_SKILLS_DIR = Path(__file__).parents[3]
_SRC = _SKILLS_DIR / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from kaggle_ai_agents.models import NewsItem
from kaggle_ai_agents.tools.news_sources import load_source_registry
from kaggle_ai_agents.tools.rss_fetcher import parse_rss_file, parse_rss_bytes
from kaggle_ai_agents.tools.security_gate import filter_items


def fetch_from_source(source: dict) -> list[NewsItem]:
    """Fetch items from a single source based on its kind.
    
    Args:
        source: source config dict with id, kind, url, etc.
        
    Returns:
        list of NewsItem records (may be empty if fetch fails)
    """
    source_id = source.get("id")
    kind = source.get("kind")
    url = source.get("url")
    
    if kind == "rss" or kind == "youtube_rss":
        # RSS sources: use rss_fetcher
        if not url:
            return []
        
        try:
            # Try to fetch from URL
            import urllib.request
            with urllib.request.urlopen(url, timeout=5) as response:
                data = response.read()
            items = parse_rss_bytes(data, source_id, limit=20)
            return items
        except Exception:
            # Silently fail for individual sources; workflow continues
            return []
    
    elif kind in ("youtube_channel", "web_scrape", "js_crawl", "structured_json", "mixed"):
        # TODO: implement adapters for these source kinds
        # For now, return empty list (stub)
        return []
    
    else:
        # Unknown source kind
        return []


def main() -> int:
    """Fetch from all configured sources, apply security gate, output JSON."""
    parser = argparse.ArgumentParser(
        description="Discover news items from configured sources"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to project.yaml config (defaults to agentic/config/project.yaml)"
    )
    parser.add_argument(
        "--sources",
        nargs="*",
        help="Optional: fetch only these source IDs"
    )
    
    args = parser.parse_args()
    
    # Load config
    config_path = args.config
    if config_path is None:
        config_path = _SKILLS_DIR / "config" / "project.yaml"
    
    try:
        sources = load_source_registry(config_path)
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Failed to load config: {e}", file=sys.stderr)
        return 1
    
    # Filter sources if --sources specified
    if args.sources:
        sources = [s for s in sources if s.get("id") in args.sources]
    
    # Fetch from all sources
    all_items: list[NewsItem] = []
    for source in sources:
        items = fetch_from_source(source)
        all_items.extend(items)
    
    # Apply security gate filter
    filtered = filter_items(all_items)
    
    # Output: passed items only (blocked items are skipped in discovery)
    output = [
        {
            "source_id": item.source_id,
            "title": item.title,
            "url": str(item.url),
            "summary": item.summary,
        }
        for item in filtered.passed
    ]
    
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
