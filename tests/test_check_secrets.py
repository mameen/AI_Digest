"""Fixture-backed tests for scripts/check_secrets.py — no mocks."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

_spec = importlib.util.spec_from_file_location("check_secrets", _SCRIPTS / "check_secrets.py")
assert _spec and _spec.loader
check_secrets = importlib.util.module_from_spec(_spec)
sys.modules["check_secrets"] = check_secrets
_spec.loader.exec_module(check_secrets)


def _fake_github_pat() -> str:
    return "ghp_" + ("a" * 36)


def _fake_openai_key() -> str:
    return "sk-" + ("b" * 24)


def _fake_home_path() -> str:
    return '{"source": "/' + "Users/alice/src/ad/AI_Digest/app" + '"}'


class CheckSecretsTest(unittest.TestCase):
    def test_clean_fixture_passes(self) -> None:
        path = ROOT / "tests/data/preflight_youtube_category.json"
        self.assertEqual(check_secrets.scan_paths([path]), [])

    def test_blocks_github_pat(self) -> None:
        findings = check_secrets.scan_line("config.yaml", 1, f"token: {_fake_github_pat()}")
        self.assertTrue(findings)
        self.assertTrue(any(f.kind == "secret" for f in findings))

    def test_blocks_home_path(self) -> None:
        findings = check_secrets.scan_line("app/deploy_manifest.json", 3, _fake_home_path())
        self.assertTrue(any("home path" in f.detail for f in findings))

    def test_allows_slack_placeholder_in_example(self) -> None:
        line = "SLACK_BOT_TOKEN=xoxb-" + "PASTE-BOT-TOKEN-HERE"
        findings = check_secrets.scan_line(
            "agentic/hermes/config/hermes.env.example",
            11,
            line,
        )
        self.assertEqual(findings, [])

    def test_allows_placeholder_assignment(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".env.example", delete=False) as fh:
            fh.write("# OPENAI_API_KEY=sk-...\n")
            path = Path(fh.name)
        try:
            self.assertEqual(check_secrets.scan_paths([path]), [])
        finally:
            path.unlink(missing_ok=True)

    def test_blocks_env_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text(f"OPENAI_API_KEY={_fake_openai_key()}\n", encoding="utf-8")
            findings = check_secrets.scan_paths([path])
            self.assertTrue(any("forbidden sensitive file" in f.detail for f in findings))

    def test_blocks_json_client_secret(self) -> None:
        line = '"client_secret": "super-real-azure-secret-not-placeholder"'
        findings = check_secrets.scan_line("config/oauth.json", 2, line)
        self.assertTrue(any("client_secret" in f.detail for f in findings))

    def test_allows_lan_ip_in_roles_yaml(self) -> None:
        path = ROOT / "agentic/hermes/admin/config/hermes_roles.yaml"
        self.assertEqual(check_secrets.scan_paths([path]), [])


if __name__ == "__main__":
    unittest.main()
