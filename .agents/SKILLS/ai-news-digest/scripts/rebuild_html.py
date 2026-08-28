"""
Rebuild a digest content HTML from content.template.html + JSON.

Also refreshes reports/index.json. Leaderboard snapshots are preserved from
the existing HTML when present, otherwise copied from legacy template.html.

Usage:
    python skills/ai-news-digest/scripts/rebuild_html.py
    python skills/ai-news-digest/scripts/rebuild_html.py 20260515120000
    python skills/ai-news-digest/scripts/rebuild_html.py --all
    python skills/ai-news-digest/scripts/rebuild_html.py --upload
    python skills/ai-news-digest/scripts/rebuild_html.py --no-ts-update
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _report_utils import (
    REPORTS_DIR,
    WORK_REPORTS_DIR,
    build_content_html,
    build_frame_html,
    leaderboards_for_prefix,
    list_digest_jsons,
    sync_work_reports,
)
from rebuild_index import write_index

BUCKET = ""
PROFILE = ""
PUBLIC_BASE = ""


def latest_prefix() -> str:
    paths = list_digest_jsons(REPORTS_DIR)
    if not paths:
        raise RuntimeError(f"No digest JSON files found in {REPORTS_DIR}")
    return paths[-1].stem


def rebuild_one(prefix: str, *, update_ts: bool = True) -> None:
    json_path = REPORTS_DIR / f"{prefix}.json"
    html_path = REPORTS_DIR / f"{prefix}.html"
    if not json_path.exists():
        raise FileNotFoundError(json_path)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    if update_ts:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        old_ts = data.get("generated_at", "")
        data["generated_at"] = now_str
        if old_ts != now_str:
            print(f"  generated_at: {old_ts} → {now_str}")

    data["filename_prefix"] = prefix
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lb = leaderboards_for_prefix(prefix)
    html = build_content_html(prefix, lb)
    html_path.write_text(html, encoding="utf-8")
    print(f"  OK {html_path.name} ({len(html):,} bytes)")


def upload(prefix: str | None = None) -> bool:
    if not BUCKET or not PROFILE:
        print("  ERROR upload requires host-configured BUCKET and PROFILE", file=sys.stderr)
        return False
    result = subprocess.run(
        ["aws", "s3", "ls", f"{BUCKET}/", "--profile", PROFILE],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("  ERROR AWS credentials check failed — skipping upload", file=sys.stderr)
        print(f"    {result.stderr.strip()}", file=sys.stderr)
        return False

    files: list[tuple[Path, str]] = [
        (REPORTS_DIR / "index.html", "text/html"),
        (REPORTS_DIR / "index.json", "application/json"),
    ]
    if prefix:
        files.extend([
            (REPORTS_DIR / f"{prefix}.html", "text/html"),
            (REPORTS_DIR / f"{prefix}.json", "application/json"),
        ])

    ok = True
    for path, content_type in files:
        if not path.exists():
            continue
        cmd = [
            "aws", "s3", "cp", str(path), f"{BUCKET}/{path.name}",
            "--profile", PROFILE, "--content-type", content_type,
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  ERROR upload {path.name}: {r.stderr.strip()}", file=sys.stderr)
            ok = False
        else:
            print(f"  OK uploaded {path.name}")
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild digest HTML (frame/content split)")
    parser.add_argument("prefix", nargs="?", help="14-digit prefix (default: latest)")
    parser.add_argument("--all", action="store_true", help="Rebuild every digest in reports/")
    parser.add_argument("--upload", action="store_true", help="Upload to S3 after rebuilding")
    parser.add_argument("--no-ts-update", dest="no_ts", action="store_true",
                        help="Do not update generated_at timestamp")
    parser.add_argument("--sync-work", action="store_true", help="Mirror reports/ to .reports/")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.all:
        prefixes = [p.stem for p in list_digest_jsons(REPORTS_DIR)]
        print(f"Rebuilding {len(prefixes)} digests")
        for prefix in prefixes:
            print(prefix)
            rebuild_one(prefix, update_ts=not args.no_ts)
    else:
        prefix = args.prefix or latest_prefix()
        print(f"Rebuilding {prefix}.html")
        rebuild_one(prefix, update_ts=not args.no_ts)

    write_index(sync_work=args.sync_work)
    (REPORTS_DIR / "index.html").write_text(build_frame_html(), encoding="utf-8")
    print("OK index.html")

    if args.upload:
        print()
        target = None if args.all else (args.prefix or latest_prefix())
        if upload(target):
            if target:
                if PUBLIC_BASE:
                    print(f"\nURL  {PUBLIC_BASE.rstrip('/')}/{target}.html")
            print(f"URL  {PUBLIC_BASE}/index.html")
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
