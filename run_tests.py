"""Single entry point for the whole test suite, across both runtimes.

Each layer is tested in the runtime it actually runs in (no mocks):
  * Python pipeline  -> unittest discovery under ``tests/``
  * Browser widget   -> ``node --test`` over ``vendor/ai-news-digest/``

Usage:  python run_tests.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JS_DIR = ROOT / "vendor" / "ai-news-digest"


def run_python() -> bool:
    print("== Python pipeline tests (unittest) ==")
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()


def run_node() -> bool:
    node = shutil.which("node")
    print("\n== Browser widget tests (node --test) ==")
    if not node:
        print("  SKIP node not found on PATH; skipping JS tests.")
        return True
    proc = subprocess.run([node, "--test", str(JS_DIR)], cwd=str(ROOT))
    return proc.returncode == 0


def main() -> int:
    ok_py = run_python()
    ok_js = run_node()
    print("\n== Summary ==")
    print(f"  python: {'PASS' if ok_py else 'FAIL'}")
    print(f"  node:   {'PASS' if ok_js else 'FAIL'}")
    return 0 if (ok_py and ok_js) else 1


if __name__ == "__main__":
    sys.exit(main())
