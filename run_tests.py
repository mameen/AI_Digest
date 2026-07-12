"""Single entry point for the whole test suite, across both runtimes.

Each layer is tested in the runtime it actually runs in (no mocks):
  * Python pipeline  -> unittest discovery under ``tests/`` and ``lib/tests/``
  * Browser widget   -> ``node --test`` over ``llm_pipeline/vendor/ai-news-digest/``

Usage:  python run_tests.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from lib.paths import LLM_PIPELINE_ROOT

ROOT = Path(__file__).resolve().parent
JS_DIR = LLM_PIPELINE_ROOT / "vendor" / "ai-news-digest"


def run_python() -> bool:
    print("== Python pipeline tests (unittest) ==")
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    suite.addTests(loader.discover(str(ROOT / "tests")))
    hermes_tests = ROOT / "agentic" / "hermes" / "tests"
    if hermes_tests.is_dir():
        suite.addTests(loader.discover(str(hermes_tests), top_level_dir=str(ROOT)))
    llm_tests = ROOT / "llm_pipeline" / "tests"
    if llm_tests.is_dir():
        suite.addTests(loader.discover(str(llm_tests), top_level_dir=str(ROOT)))
    lib_tests = ROOT / "lib" / "tests"
    if lib_tests.is_dir():
        suite.addTests(loader.discover(str(lib_tests), top_level_dir=str(ROOT)))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return result.wasSuccessful()


def run_node() -> bool:
    node = shutil.which("node")
    print("\n== Browser widget tests (node --test) ==")
    if not node:
        print("  SKIP node not found on PATH; skipping JS tests.")
        return True
    js_tests = sorted(JS_DIR.glob("*.test.js"))
    if not js_tests:
        print("  SKIP no *.test.js under vendor/ai-news-digest")
        return True
    proc = subprocess.run([node, "--test", *[str(p) for p in js_tests]], cwd=str(ROOT))
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
