"""Configuration loading for all implementations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any


def load_config(backend: str, override_model: str = None, override_host: str = None) -> Dict[str, Any]:
    """Load backend-specific configuration.
    
    Args:
        backend: One of "fully_scripted", "google_adk", "ollama_agent"
        override_model: Override model (Ollama only)
        override_host: Override host (Ollama only)
    
    Returns:
        Configuration dict with backend-specific settings
    """

    configs = {
        "fully_scripted": {
            "backend": "script",
            "description": "No LLM — keyword-based ranking (fast, deterministic)",
            "requires": [],
        },
        "google_adk": {
            "backend": "google",
            "description": "Google Gemini API (requires GEMINI_API_KEY env var)",
            "requires": ["GEMINI_API_KEY"],
        },
        "ollama_agent": {
            "backend": "ollama",
            "description": "Local Ollama LLM with LangChain",
            "requires": [],
            "model": "qwen2.5-coder:14b",
            "host": "http://localhost:11434",
        },
    }

    if backend not in configs:
        raise ValueError(f"Unknown backend: {backend}. Choose from: {list(configs.keys())}")

    cfg = dict(configs[backend])

    # Ollama overrides
    if override_model:
        cfg["model"] = override_model
    if override_host:
        cfg["host"] = override_host

    # Verify required env vars
    for req in cfg.get("requires", []):
        if not os.getenv(req):
            raise EnvironmentError(f"Required env var not set: {req}")

    return cfg
