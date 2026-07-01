"""Shared Instructor + OpenAI-compatible client for local Ollama."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Any, Callable, Tuple


def ensure_ollama_ready(cfg: dict[str, Any]) -> None:
    """Fail fast with a clear message if local Ollama is not reachable."""
    llm = cfg["llm"]
    if llm.get("provider", "ollama") != "ollama":
        return

    base = str(llm.get("base_url", "http://localhost:11434/v1")).rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    tags_url = f"{base}/api/tags"
    model = llm.get("model", "qwen3.6:35b")

    try:
        with urllib.request.urlopen(tags_url, timeout=5) as resp:
            payload = resp.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SystemExit(
            f"Local Ollama not reachable at {base}.\n"
            f"  Start Ollama, then: ollama pull {model}\n"
            f"  Or run: python run.py --skeleton-only"
        ) from exc

    if model not in payload and f'"{model}"' not in payload:
        print(f"  WARN model {model!r} not found in Ollama tags. Run: ollama pull {model}")


def make_client(cfg: dict[str, Any]) -> Tuple[Any, str, int]:
    """Return (instructor client, model name, max_retries). Uses local Ollama by default."""
    try:
        import instructor
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit(
            "llm.enabled requires instructor + openai packages.\n"
            "  pip install -r requirements.txt"
        ) from exc

    ensure_ollama_ready(cfg)

    llm = cfg["llm"]
    provider = llm.get("provider", "ollama")
    max_retries = int(llm.get("max_retries", 3))
    model = llm.get("model", "qwen3.6:35b")

    if provider == "ollama":
        client = instructor.from_openai(
            OpenAI(
                base_url=llm.get("base_url", "http://localhost:11434/v1"),
                api_key="ollama",
            ),
            mode=instructor.Mode.JSON,
        )
    elif provider == "openai":
        print("  WARN llm.provider=openai. Repo default is local Ollama; override only when needed.")
        client = instructor.from_openai(OpenAI(), mode=instructor.Mode.JSON)
    else:
        raise SystemExit(
            f"Unsupported llm.provider: {provider!r}. "
            "Use ollama (preferred) or openai."
        )

    return client, model, max_retries


def make_raw_chat(cfg: dict[str, Any]) -> Tuple[Callable[[list[dict[str, str]]], str], str]:
    """Return ``(chat, model)`` for free-form (non-Instructor) chat completions.

    The tool-calling loop needs raw text replies (a single JSON action per turn),
    which do not flow through ``instructor.Mode.JSON``. This builds a plain
    OpenAI-compatible client against the same endpoint. ``chat(messages) -> str``.
    """
    from openai import OpenAI

    llm = cfg["llm"]
    provider = llm.get("provider", "ollama")
    model = llm.get("model", "qwen3.6:35b")
    if provider == "ollama":
        client = OpenAI(base_url=llm.get("base_url", "http://localhost:11434/v1"), api_key="ollama")
    else:
        client = OpenAI()

    def chat(messages: list[dict[str, str]]) -> str:
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0)
        return resp.choices[0].message.content or ""

    return chat, model
