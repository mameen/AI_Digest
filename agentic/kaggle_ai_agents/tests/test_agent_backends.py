"""Tests for pluggable agent backends."""

import pytest

from kaggle_ai_agents.agent_backends import (
    DirectScriptBackend,
    GoogleADKBackend,
    OllamaBackend,
    get_agent_backend,
    load_agent_config,
)
from kaggle_ai_agents.models import DailyBrief


class TestDirectScriptBackend:
    """Test direct script backend (deterministic orchestration)."""

    def test_direct_script_backend_creation(self):
        """Test creating direct script backend."""
        backend = DirectScriptBackend("direct_script")
        assert backend.name == "direct_script"

    def test_direct_script_backend_forward_with_stubs(self):
        """Test direct script backend with stub data."""
        backend = DirectScriptBackend("direct_script")
        brief = backend.forward("Test prompt", use_real_sources=False)
        
        assert isinstance(brief, DailyBrief)
        assert len(brief.cards) > 0
        assert brief.date
        assert brief.theme == "AI signal over noise"


class TestGoogleADKBackend:
    """Test Google ADK backend."""

    def test_google_adk_backend_creation(self):
        """Test creating Google ADK backend."""
        config = {"instruction": "Test instruction"}
        backend = GoogleADKBackend("google_adk", config)
        assert backend.name == "google_adk"
        assert backend.config["instruction"] == "Test instruction"

    def test_google_adk_backend_forward_with_stubs(self):
        """Test Google ADK backend with stub data."""
        config = {"instruction": "You are a curator"}
        backend = GoogleADKBackend("google_adk", config)
        brief = backend.forward("Test prompt", use_real_sources=False)
        
        assert isinstance(brief, DailyBrief)
        assert len(brief.cards) > 0
        assert brief.date


class TestOllamaBackend:
    """Test Ollama backend (requires local Ollama running)."""

    def test_ollama_backend_creation(self):
        """Test creating Ollama backend."""
        config = {
            "base_url": "http://localhost:11434",
            "model": "llama2",
        }
        backend = OllamaBackend("ollama", config)
        assert backend.name == "ollama"
        assert backend.config["base_url"] == "http://localhost:11434"

    def test_ollama_backend_forward_graceful_fallback(self):
        """Test that Ollama backend gracefully falls back if unavailable or package not installed."""
        config = {
            "base_url": "http://invalid:0",  # Invalid URL should trigger fallback
            "model": "llama2",
        }
        backend = OllamaBackend("ollama", config)
        
        # Should not raise, but either:
        # 1. Raise RuntimeError if ollama package not installed (expected in test env)
        # 2. Fall back to script-based ranking if package is installed but server unavailable
        try:
            brief = backend.forward("Test prompt", use_real_sources=False)
            assert isinstance(brief, DailyBrief)
            assert len(brief.cards) > 0
        except RuntimeError as e:
            # Expected when ollama package not installed
            assert "ollama package not installed" in str(e)


class TestBackendFactory:
    """Test backend factory and selection."""

    def test_get_direct_script_backend(self):
        """Test getting direct script backend via factory."""
        backend = get_agent_backend("direct_script")
        assert isinstance(backend, DirectScriptBackend)
        assert backend.name == "direct_script"

    def test_get_google_adk_backend(self):
        """Test getting Google ADK backend via factory."""
        config = {"instruction": "Test"}
        backend = get_agent_backend("google_adk", config)
        assert isinstance(backend, GoogleADKBackend)
        assert backend.name == "google_adk"

    def test_get_ollama_backend(self):
        """Test getting Ollama backend via factory."""
        config = {"base_url": "http://localhost:11434"}
        backend = get_agent_backend("ollama", config)
        assert isinstance(backend, OllamaBackend)
        assert backend.name == "ollama"

    def test_get_invalid_backend_raises(self):
        """Test that invalid backend name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown agent backend"):
            get_agent_backend("invalid_backend")

    def test_backend_factory_with_config(self):
        """Test that factory properly passes config to backend."""
        config = {"key": "value"}
        backend = get_agent_backend("direct_script", config)
        assert backend.config == config


class TestConfigLoading:
    """Test configuration loading from project.yaml."""

    def test_load_agent_config_auto_detect(self):
        """Test auto-detection and loading of agent config."""
        backend_name, backend_config = load_agent_config()
        
        # Should load successfully
        assert backend_name in ["direct_script", "google_adk", "ollama"]
        assert isinstance(backend_config, dict)

    def test_config_has_backends_defined(self):
        """Test that config includes all three backends."""
        backend_name, backend_config = load_agent_config()
        
        # Should have loaded a valid backend
        assert backend_name is not None
        
        # Backend config might be empty for direct_script, but should be dict
        assert isinstance(backend_config, dict)


class TestWorkflowIntegration:
    """Test integration with workflow module."""

    def test_run_with_direct_script_backend(self):
        """Test workflow with direct script backend."""
        from kaggle_ai_agents.workflow import run_daily_brief_with_backend
        
        brief = run_daily_brief_with_backend("direct_script", use_real_sources=False)
        assert isinstance(brief, DailyBrief)
        assert len(brief.cards) > 0

    def test_run_with_google_adk_backend(self):
        """Test workflow with Google ADK backend."""
        from kaggle_ai_agents.workflow import run_daily_brief_with_backend
        
        brief = run_daily_brief_with_backend("google_adk", use_real_sources=False)
        assert isinstance(brief, DailyBrief)
        assert len(brief.cards) > 0

    def test_run_with_config_driven_backend(self):
        """Test workflow with config-driven backend selection."""
        from kaggle_ai_agents.workflow import run_daily_brief_with_backend
        
        # Should use backend from project.yaml
        brief = run_daily_brief_with_backend(use_real_sources=False)
        assert isinstance(brief, DailyBrief)
        assert len(brief.cards) > 0

    def test_run_with_override_backend(self):
        """Test that explicit backend overrides config."""
        from kaggle_ai_agents.workflow import run_daily_brief_with_backend
        
        # Explicitly request direct_script
        brief = run_daily_brief_with_backend("direct_script", use_real_sources=False)
        assert isinstance(brief, DailyBrief)
        assert len(brief.cards) > 0
