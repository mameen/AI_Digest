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
    
    elif kind == "structured_json":
        # Structured JSON API sources (SWE-bench, EvalPlus, etc.)
        if not url:
            return []
        
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=5) as response:
                data = response.read().decode('utf-8')
            
            payload = json.loads(data)
            
            # Map API response to NewsItem records based on source ID
            items: list[NewsItem] = []
            
            if source_id == "swebench-leaderboard":
                # SWE-bench: list of leaderboard dicts with results
                if isinstance(payload, dict) and "leaderboards" in payload:
                    for board in payload.get("leaderboards", [])[:3]:  # Top 3 boards
                        board_name = board.get("name", "unknown")
                        results = board.get("results", [])
                        for result in results[:2]:  # Top 2 results per board
                            model_name = result.get("name", "Unknown")
                            resolved_pct = result.get("resolved_pct", result.get("resolved", "N/A"))
                            items.append(NewsItem(
                                source_id=source_id,
                                title=f"SWE-bench {board_name}: {model_name}",
                                url="https://swe-bench.github.io/leaderboard/",
                                summary=f"Resolved: {resolved_pct}"
                            ))
            
            elif source_id == "evalplus-results":
                # EvalPlus: dict of models with their scores
                if isinstance(payload, dict):
                    for idx, (model_name, data) in enumerate(list(payload.items())[:10]):  # Top 10 models
                        pass_rate = data.get("pass@1", {})
                        if isinstance(pass_rate, dict):
                            humaneval = pass_rate.get("humaneval", "N/A")
                        else:
                            humaneval = pass_rate
                        items.append(NewsItem(
                            source_id=source_id,
                            title=f"EvalPlus: {model_name}",
                            url=data.get("link", "https://evalplus.github.io/"),
                            summary=f"HumanEval pass@1: {humaneval}%"
                        ))
            
            return items
        
        except Exception:
            # Silently fail for individual sources; workflow continues
            return []
    
    elif kind == "web_scrape":
        # Web scrape sources: fetch HTML and parse by source ID
        if not url:
            return []
        
        try:
            import urllib.request
            from bs4 import BeautifulSoup
            
            with urllib.request.urlopen(url, timeout=5) as response:
                html = response.read()
            
            soup = BeautifulSoup(html, 'html.parser')
            items: list[NewsItem] = []
            
            if source_id == "arxiv-cs-ai" or source_id.startswith("arxiv-"):
                # arXiv recent listings: parse article list
                # Structure: <dt> with <a href="/abs/..."> id link, then <dd> with title and abstract
                articles = soup.find_all('dt')
                for dt in articles[:10]:  # Top 10 recent papers
                    try:
                        # Get arxiv ID from link href (not text content)
                        id_elem = dt.find('a', href=True)
                        if not id_elem or 'href' not in id_elem.attrs:
                            continue
                        href = id_elem.get('href', '')
                        # Extract arxiv ID from /abs/XXXX.XXXXX format
                        arxiv_id = href.split('/abs/')[-1] if '/abs/' in href else None
                        if not arxiv_id:
                            continue
                        url_item = f"https://arxiv.org/abs/{arxiv_id}"
                        
                        # Get title and abstract from following dd
                        dd = dt.find_next('dd')
                        if not dd:
                            continue
                        
                        # Title is in div.list-title
                        title_div = dd.find('div', class_='list-title')
                        if title_div:
                            title_text = title_div.get_text(strip=True)
                            # Remove 'Title:' prefix if present
                            if title_text.startswith('Title:'):
                                title_text = title_text[6:].strip()
                        else:
                            title_text = "Unknown"
                        
                        # Summary from full text (first 200 chars)
                        summary = dd.get_text(strip=True)[:200]
                        
                        items.append(NewsItem(
                            source_id=source_id,
                            title=title_text,
                            url=url_item,
                            summary=summary
                        ))
                    except Exception:
                        continue
            
            elif source_id == "huggingface-papers":
                # HuggingFace Papers: parse paper cards
                # Structure: article.paper-card with h3 title and p.summary
                papers = soup.find_all('article', class_='paper-card')
                for paper in papers[:10]:  # Top 10 papers
                    try:
                        title_elem = paper.find('h3')
                        if not title_elem:
                            continue
                        title = title_elem.get_text(strip=True)
                        
                        # Get link and summary
                        link_elem = paper.find('a', href=True)
                        link = link_elem['href'] if link_elem else "https://huggingface.co/papers"
                        if not link.startswith('http'):
                            link = f"https://huggingface.co/papers{link}"
                        
                        summary_elem = paper.find('p', class_='summary')
                        summary = summary_elem.get_text(strip=True)[:200] if summary_elem else ""
                        
                        items.append(NewsItem(
                            source_id=source_id,
                            title=title,
                            url=link,
                            summary=summary
                        ))
                    except Exception:
                        continue
            
            return items
        
        except Exception:
            # Silently fail for individual sources; workflow continues
            return []
    
    elif kind in ("youtube_channel", "js_crawl", "mixed"):
        # youtube_channel: Use yt-dlp to fetch latest videos from channel
        if kind == "youtube_channel":
            if not url:
                return []
            
            try:
                import subprocess
                
                # Use yt-dlp to get latest videos from channel
                # -j for JSON output (line-separated)
                # --flat-playlist to get video list without downloading
                # --max-downloads to limit
                result = subprocess.run(
                    [
                        "yt-dlp",
                        "-j",
                        "--max-downloads", "15",
                        "--flat-playlist",
                        url
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30  # Increased timeout for YouTube channels
                )
                
                if result.returncode != 0:
                    return []
                
                items: list[NewsItem] = []
                
                # yt-dlp outputs line-separated JSON when using -j (JSONL format)
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    try:
                        video = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        continue
                    
                    try:
                        # Handle None entries (deleted/unavailable videos)
                        if video is None:
                            continue
                        
                        title = video.get("title", "Untitled")
                        video_id = video.get("id", "")
                        if not video_id:
                            continue
                        
                        # Build YouTube URL
                        url_item = f"https://www.youtube.com/watch?v={video_id}"
                        
                        # Build summary with view count, upload date
                        view_count = video.get("view_count", "N/A")
                        upload_date = video.get("upload_date", "")
                        if upload_date and len(upload_date) >= 8:
                            # Format YYYYMMDD as YYYY-MM-DD
                            upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
                        
                        summary = f"Views: {view_count}, Uploaded: {upload_date}"
                        
                        items.append(NewsItem(
                            source_id=source_id,
                            title=title,
                            url=url_item,
                            summary=summary
                        ))
                    except Exception:
                        continue
                
                return items[:10]  # Return top 10 videos
            
            except subprocess.TimeoutExpired:
                # Timeout - return what we have so far or empty
                return []
            except FileNotFoundError:
                # yt-dlp not installed
                return []
            except Exception:
                # Any other error (parsing, etc.)
                return []
        
        elif kind == "js_crawl":
            # JS-crawl sources: leaderboards and similar dynamic pages
            # For now, extract from schema.org JSON-LD when available
            if not url:
                return []
            
            try:
                import urllib.request
                import re
                
                with urllib.request.urlopen(url, timeout=10) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                
                items: list[NewsItem] = []
                
                # Extract JSON-LD schema (FAQ format often has leaderboard data)
                match = re.search(r'<script type="application/ld\+json">({.*?})</script>', html, re.DOTALL)
                if match:
                    try:
                        schema_data = json.loads(match.group(1))
                        
                        # Extract FAQ questions and answers
                        for idx, entity in enumerate(schema_data.get('mainEntity', [])[:5]):  # Top 5 QA
                            try:
                                question = entity.get('name', '')
                                answer = entity.get('acceptedAnswer', {}).get('text', '')
                                
                                if question and answer and len(answer) > 30:
                                    # Create a NewsItem from the FAQ entry
                                    summary = answer[:200]
                                    items.append(NewsItem(
                                        source_id=source_id,
                                        title=question,
                                        url=url,
                                        summary=summary
                                    ))
                            except Exception:
                                continue
                    except (json.JSONDecodeError, ValueError):
                        pass
                
                # Fallback: try to extract model mentions from HTML (generic backup)
                if not items:
                    # Simple fallback: look for common leaderboard patterns
                    pass
                
                return items
            
            except Exception:
                # Timeouts, network errors, etc. - gracefully fail
                return []
        
        # TODO: implement mixed adapter
        # - mixed: Combine multiple adapters
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
