#!/usr/bin/env python3
"""Presidio PII/PHI scan.

  python scripts/audit_pii.py --staged
  python scripts/audit_pii.py --all
  python scripts/audit_pii.py --all --observe-piiignore   # opt-in .piiignore exemptions

Policy:
- Staged / tracked: scan all commit content (``.piiignore`` off unless ``--observe-piiignore``).
- ``--all``: also warn about local gitignored sensitive trees on disk.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from scan_ignore import (  # noqa: E402
    alarm_commit_paths,
    format_local_warnings,
    load_patterns,
    local_sensitive_warnings,
    should_skip_audit_path,
)

_FLAG_ENTITIES = frozenset(
    {
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "US_SSN",
        "CREDIT_CARD",
        "US_BANK_NUMBER",
        "US_DRIVER_LICENSE",
        "US_PASSPORT",
        "IBAN_CODE",
        "IP_ADDRESS",
        "CRYPTO",
        "UK_NHS",
        "MEDICAL_LICENSE",
        "PERSON",
    }
)
_MIN_SCORE = 0.65
_PERSON_MIN_SCORE = 0.80

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".py",
    ".yaml",
    ".yml",
    ".json",
    ".jsonl",
    ".toml",
    ".sh",
    ".env",
    ".example",
    ".eml",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".xml",
    ".csv",
    ".rst",
    ".ini",
    ".cfg",
    ".sql",
}

_ANALYZER = None


def _fail(msg: str) -> None:
    print(f"✗ PII audit: {msg}", file=sys.stderr)
    sys.exit(1)


def _staged_paths() -> list[Path]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return []
    return [REPO / line.strip() for line in out.stdout.splitlines() if line.strip()]


def _tracked_paths() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return []
    return [REPO / line.strip() for line in out.stdout.splitlines() if line.strip()]


def _rel(path: Path) -> str:
    return path.resolve().relative_to(REPO.resolve()).as_posix()


def _alarm_forbidden(paths: list[Path]) -> None:
    alarm_commit_paths([_rel(p) for p in paths])


def _is_text_candidate(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return path.name in {".piiignore", ".ignorepii", ".gitleaksignore", ".env.example"}


def _get_analyzer():
    global _ANALYZER
    if _ANALYZER is not None:
        return _ANALYZER
    try:
        from presidio_analyzer import AnalyzerEngine
        from presidio_analyzer.nlp_engine import NlpEngineProvider
    except ImportError:
        _fail(
            "presidio-analyzer not installed — run: pip install -r requirements-dev.txt\n"
            "  python -m spacy download en_core_web_sm"
        )

    for model in ("en_core_web_lg", "en_core_web_sm"):
        try:
            provider = NlpEngineProvider(
                nlp_configuration={
                    "nlp_engine_name": "spacy",
                    "models": [{"lang_code": "en", "model_name": model}],
                }
            )
            _ANALYZER = AnalyzerEngine(nlp_engine=provider.create_engine())
            return _ANALYZER
        except Exception:
            continue
    _fail(
        "spaCy English model missing — run: python -m spacy download en_core_web_sm"
    )


_ALLOWLISTED_EMAIL_DOMAINS = frozenset(
    {
        "example.com",
        "example.org",
        "example.net",
        "test.com",
        "localhost",
        "invalid",
        "acme.com",
        "cursor.com",
        "anthropic.com",
    }
)


def _entities_for_path(rel: str) -> frozenset[str]:
    ents: set[str] = set(_FLAG_ENTITIES)
    if rel.endswith(".py") or rel.endswith(".md") or rel.endswith(".yaml") or rel.endswith(".yml"):
        ents.discard("PERSON")
    return frozenset(ents)


def _scan_text(rel: str, text: str, analyzer) -> list[tuple[int, str, float]]:
    if not text.strip():
        return []
    allowed = _entities_for_path(rel)
    try:
        results = analyzer.analyze(text=text, language="en")
    except Exception:
        return []
    hits: list[tuple[int, str, float]] = []
    for r in results:
        if r.entity_type not in allowed:
            continue
        if r.entity_type == "EMAIL_ADDRESS":
            email = text[r.start : r.end]
            domain = email.split("@", 1)[-1].lower() if "@" in email else ""
            if domain in _ALLOWLISTED_EMAIL_DOMAINS:
                continue
        min_score = _PERSON_MIN_SCORE if r.entity_type == "PERSON" else _MIN_SCORE
        if r.score < min_score:
            continue
        line_no = text.count("\n", 0, r.start) + 1
        hits.append((line_no, r.entity_type, r.score))
    return hits


def scan_paths(
    paths: list[Path],
    patterns: tuple[str, ...],
    *,
    observe_piiignore: bool,
) -> list[str]:
    analyzer = _get_analyzer()
    errors: list[str] = []
    for path in paths:
        rel = _rel(path)
        if should_skip_audit_path(rel, patterns, observe_piiignore=observe_piiignore):
            continue
        if not _is_text_candidate(path):
            continue
        try:
            raw = path.read_bytes()
        except OSError as exc:
            errors.append(f"{rel}: cannot read ({exc})")
            continue
        if b"\x00" in raw[:4096]:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, entity, score in _scan_text(rel, text, analyzer):
            errors.append(f"[pii] {rel}:{line_no} — Presidio {entity} (score {score:.2f})")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Presidio PII audit.")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--observe-piiignore",
        action="store_true",
        help="opt-in: honor .piiignore exemptions (default: scan commit content fully)",
    )
    args = parser.parse_args(argv)

    patterns = load_patterns(REPO)
    if args.staged:
        paths = _staged_paths()
        _alarm_forbidden(paths)
    elif args.all:
        paths = _tracked_paths()
        _alarm_forbidden(paths)
        msg = format_local_warnings(
            local_sensitive_warnings(REPO, patterns, observe_piiignore=args.observe_piiignore)
        )
        if msg:
            print(msg, file=sys.stderr)
    else:
        parser.print_help()
        return 0

    if not paths:
        return 0

    errors = scan_paths(paths, patterns, observe_piiignore=args.observe_piiignore)
    if not errors:
        return 0

    print("ERROR: PII audit failed — possible sensitive data (Presidio):\n", file=sys.stderr)
    for line in errors[:50]:
        print(f"  {line}", file=sys.stderr)
    if len(errors) > 50:
        print(f"  … and {len(errors) - 50} more", file=sys.stderr)
    print(
        "\nCommit content is scanned by default."
        " Use --observe-piiignore only to apply .piiignore exemptions.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
