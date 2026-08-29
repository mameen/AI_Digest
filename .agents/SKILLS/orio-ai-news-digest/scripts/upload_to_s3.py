"""
Upload a digest (HTML + JSON pair) to S3.

Usage:
    python scripts/upload_to_s3.py                     # upload the latest digest
    python scripts/upload_to_s3.py 20260501120000       # upload a specific prefix
    python scripts/upload_to_s3.py --check              # check credentials only

Requires: pip install boto3   (or use the AWS CLI via subprocess fallback)
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent.parent.parent / "reports"
BUCKET = ""
PROFILE = ""
PUBLIC_BASE = ""


def latest_prefix() -> str:
    prefixes = sorted(
        p.stem for p in REPORTS_DIR.glob("*.json")
        if len(p.stem) == 14 and p.stem.isdigit()
    )
    if not prefixes:
        raise RuntimeError(f"No digest files found in {REPORTS_DIR}")
    return prefixes[-1]


def check_credentials() -> bool:
    if not BUCKET or not PROFILE:
        print("S3 destination is not configured by the host", file=sys.stderr)
        return False
    """Return True if staging profile credentials are valid."""
    result = subprocess.run(
        ["aws", "s3", "ls", f"{BUCKET}/", "--profile", PROFILE],
        capture_output=True, text=True
    )
    if "ExpiredToken" in result.stderr or "InvalidClientTokenId" in result.stderr:
        return False
    if result.returncode != 0 and result.stderr:
        print(f"AWS error: {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def upload_file(local_path: Path, s3_key: str, content_type: str) -> bool:
    cmd = [
        "aws", "s3", "cp", str(local_path),
        f"{BUCKET}/{s3_key}",
        "--profile", PROFILE,
        "--content-type", content_type,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ✗ {result.stderr.strip()}", file=sys.stderr)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Upload AI digest to S3")
    parser.add_argument("prefix", nargs="?", help="14-digit timestamp prefix (default: latest)")
    parser.add_argument("--check", action="store_true", help="Check credentials only, no upload")
    args = parser.parse_args()

    print("Checking AWS staging credentials...", end=" ", flush=True)
    if not check_credentials():
        print("EXPIRED")
        print("\nCredentials have expired. Re-authenticate with:")
        print("  aws sso login --profile staging")
        print("  # or use your usual credential refresh method")
        sys.exit(1)
    print("OK")

    if args.check:
        sys.exit(0)

    prefix = args.prefix or latest_prefix()
    html_path = REPORTS_DIR / f"{prefix}.html"
    json_path = REPORTS_DIR / f"{prefix}.json"

    for path in [html_path, json_path]:
        if not path.exists():
            print(f"File not found: {path}", file=sys.stderr)
            sys.exit(1)

    index_files = [
        (REPORTS_DIR / "index.html", "text/html"),
        (REPORTS_DIR / "index.json", "application/json"),
    ]

    # Read summary from JSON for confirmation
    try:
        data = json.loads(json_path.read_text())
        summary = data.get("summary", "")
        story_count = sum(len(c["stories"]) for c in data.get("categories", []))
        print(f"\nDigest: {prefix}")
        print(f"Stories: {story_count}")
        print(f"Summary: {summary[:100]}{'…' if len(summary) > 100 else ''}\n")
    except Exception:
        pass

    print(f"Uploading {prefix}.html ...", end=" ", flush=True)
    if upload_file(html_path, f"{prefix}.html", "text/html"):
        print("done")

    print(f"Uploading {prefix}.json ...", end=" ", flush=True)
    if upload_file(json_path, f"{prefix}.json", "application/json"):
        print("done")

    for path, content_type in index_files:
        if path.exists():
            print(f"Uploading {path.name} ...", end=" ", flush=True)
            if upload_file(path, path.name, content_type):
                print("done")

    print(f"\nURL  {PUBLIC_BASE}/{prefix}.html")
    print(f"URL  {PUBLIC_BASE}/index.html")


if __name__ == "__main__":
    main()
