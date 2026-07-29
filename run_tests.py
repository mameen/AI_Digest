"""Single entry point for the whole test suite, across both runtimes.

Each layer is tested in the runtime it actually runs in (no mocks):
  * Python pipeline  -> unittest discovery under ``tests/`` and ``lib/tests/``
  * Browser widget   -> ``node --test`` over ``llm_pipeline/vendor/ai-news-digest/``

Usage:
  python run_tests.py              # plain test run
  python run_tests.py --coverage   # run with coverage report
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


def run_python(coverage: bool = False) -> bool:
    print("== Python pipeline tests (unittest) ==")
    if coverage:
        print("  Running under coverage (parallel mode)...")
        # Use coverage parallel mode: one process per test directory, then merge
        test_dirs = []
        for label, base in [
            ("root/tests", ROOT / "tests"),
            ("hermes", ROOT / "agentic" / "hermes" / "tests"),
            ("llm_pipeline", ROOT / "llm_pipeline" / "tests"),
            ("lib", ROOT / "lib" / "tests"),
        ]:
            if base.is_dir():
                test_dirs.append((label, base))

        cov_procs = []
        for label, tdir in test_dirs:
            cmd = [
                sys.executable, "-m", "coverage",
                "run", "--parallel-mode", "-m", "unittest",
                "discover", "-s", str(tdir),
                "-p", "test_*.py",
                "-t", str(ROOT),
            ]
            cov_procs.append(subprocess.run(cmd))

        # Merge parallel data and report
        subprocess.run([sys.executable, "-m", "coverage", "combine"], check=False)
        print("\n  Generating coverage report...")
        subprocess.run([sys.executable, "-m", "coverage", "report"], check=False)
        subprocess.run([sys.executable, "-m", "coverage", "html"], check=False)
        return all(p.returncode == 0 for p in cov_procs)
    else:
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
    coverage = "--coverage" in sys.argv
    ok_py = run_python(coverage=coverage)
    ok_js = run_node()
    print("\n== Summary ==")
    print(f"  python: {'PASS' if ok_py else 'FAIL'}")
    print(f"  node:   {'PASS' if ok_js else 'FAIL'}")
    return 0 if (ok_py and ok_js) else 1


if __name__ == "__main__":
    sys.exit(main())
