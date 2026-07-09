"""Backward-compatible entry — prefer ``python run.py --server``."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.local_server import DEFAULT_PORT, serve_local  # noqa: E402


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="AI Digest local site (use run.py --server)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    print("Tip: python run.py --server")
    serve_local(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
