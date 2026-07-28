"""Tests for lib.config — Config class, load_config, defaults."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from lib.config import (
    Config,
    _apply_llm_defaults,
    _default_llm,
    load_config,
)


class TestDefaultLlm(unittest.TestCase):
    """_default_llm returns the expected local Ollama defaults."""

    def test_returns_dict(self):
        result = _default_llm()
        self.assertIsInstance(result, dict)

    def test_provider_is_ollama(self):
        self.assertEqual(_default_llm()["provider"], "ollama")

    def test_model_is_llama31(self):
        self.assertIn("llama3.1", _default_llm()["model"])

    def test_base_url_is_local(self):
        self.assertEqual(_default_llm()["base_url"], "http://localhost:11434/v1")


class TestApplyLlmDefaults(unittest.TestCase):
    """_apply_llm_defaults merges defaults into a mutable config dict."""

    def test_empty_dict_gets_defaults(self):
        cfg = {}
        _apply_llm_defaults(cfg)
        self.assertEqual(cfg["llm"]["provider"], "ollama")
        self.assertIn("llama3.1", cfg["llm"]["model"])
        self.assertEqual(cfg["llm"]["base_url"], "http://localhost:11434/v1")

    def test_existing_provider_not_overridden(self):
        cfg = {"llm": {"provider": "openai"}}
        _apply_llm_defaults(cfg)
        self.assertEqual(cfg["llm"]["provider"], "openai")

    def test_partial_dict_gets_missing_keys(self):
        cfg = {"llm": {"provider": "ollama", "model": "custom:latest"}}
        _apply_llm_defaults(cfg)
        self.assertIn("base_url", cfg["llm"])  # was missing, now filled


class TestConfigClass(unittest.TestCase):
    """Config class — immutable wrapper around config dict."""

    def test_init_applies_defaults(self):
        cfg = Config({"llm": {}})
        self.assertEqual(cfg.llm["provider"], "ollama")

    def test_llm_property_returns_dict(self):
        cfg = Config({"llm": {"provider": "ollama"}})
        self.assertIsInstance(cfg.llm, dict)

    def test_raw_property_returns_full_data(self):
        data = {"llm": {}, "ingestion": {}}
        cfg = Config(data)
        self.assertEqual(cfg.raw["ingestion"], {})

    def test_no_llm_key_creates_empty(self):
        cfg = Config({})
        self.assertEqual(cfg.llm["provider"], "ollama")  # defaults applied


class TestLoadConfig(unittest.TestCase):
    """load_config loads YAML and merges .env."""

    def test_loads_from_path(self):
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write("llm:\n  provider: ollama\n")
            f.flush()
            cfg = load_config(Path(f.name))
        Path(f.name).unlink()
        self.assertEqual(cfg["llm"]["provider"], "ollama")

    def test_env_vars_not_mutated_without_dotenv(self):
        """load_config should not mutate os.environ when .env is absent."""
        with tempfile.NamedTemporaryFile(
            suffix=".yaml", mode="w", encoding="utf-8", delete=False
        ) as f:
            f.write("llm:\n  provider: ollama\n")
            f.flush()
            before = os.environ.get("_AI_DIGEST_TEST_KEY")
            load_config(Path(f.name))
            after = os.environ.get("_AI_DIGEST_TEST_KEY")
        Path(f.name).unlink()
        self.assertIsNone(before)
        self.assertIsNone(after)


if __name__ == "__main__":
    unittest.main()
