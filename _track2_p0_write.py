"""Track 2 P0 extraction: write lib/ modules + deprecation shims."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ── lib/schema.py (OOP hierarchy) ───────────────────────────────────────────

lib_schema = '''\
"""Pydantic schema for Instructor / validation (matches digest JSON shape).

Organized as a hierarchy of domain models rather than flat functions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------

class ResourceLink(BaseModel):
    """A link to an external resource (GitHub, X, HuggingFace, etc.)."""

    name: str
    url: str
    kind: str | None = None  # github, x, linkedin, huggingface, arxiv, web


class Story(BaseModel):
    """Canonical story model — the atomic unit of the digest."""

    id: str
    title: str
    summary: str
    source: str
    url: str | None = None
    significance: int = Field(ge=1, le=5)
    novelty: int = Field(ge=1, le=5)
    relevance_design: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None
    source_pending: bool = False
    provenance: str | None = None
    channel_key: str | None = None
    channel_label: str | None = None
    topic: str | None = None
    links: list[ResourceLink] = Field(default_factory=list)


class Category(BaseModel):
    """A digest category containing zero or more stories."""

    id: str
    label: str
    icon: str
    stories: list[Story] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Enrichment models (used by the LLM response path)
# ---------------------------------------------------------------------------

class StoryEnrich(BaseModel):
    """Enriched story; ids/urls preserved from preflight."""

    id: str
    title: str
    summary: str
    source: str
    url: str | None = None
    significance: int = Field(ge=1, le=5)
    novelty: int = Field(ge=1, le=5)
    relevance_design: int = Field(ge=1, le=5)
    tags: list[str] = Field(default_factory=list)
    image_url: str | None = None
    source_pending: bool = False
    channel_key: str | None = None
    channel_label: str | None = None
    topic: str | None = None
    # NOTE: no `provenance` here on purpose — StoryEnrich is the LLM response
    # model. Provenance is deterministic pipeline metadata stamped after enrich
    # (see enrich._with_provenance); the model must never author it.


class CategoryStories(BaseModel):
    """A category with its enriched stories."""

    stories: list[StoryEnrich]


class GapCategories(BaseModel):
    """New editorial categories authored from ingestion context."""

    categories: list[Category]


# ---------------------------------------------------------------------------
# Top-level document models
# ---------------------------------------------------------------------------

class DigestDocument(BaseModel):
    """The complete digest output — the deterministic tail contract."""

    generated_at: str
    filename_prefix: str
    summary: str
    aisearch_video_url: str | None = None
    aisearch_video_label: str | None = None
    aisearch_video_description: str | None = None
    categories: list[Category]
    visualizations: dict[str, Any] | None = None


class DigestHeader(BaseModel):
    """Lightweight header for the digest report."""

    summary: str
    aisearch_video_url: str | None = None
    aisearch_video_label: str | None = None
    top_stories: list[Any] | None = None
    report_source: str | None = None
    report_source_badge: str | None = None
    report_source_label: str | None = None
'''

# ── lib/config.py (OOP Config class) ────────────────────────────────────────

lib_config = '''\
"""Configuration loader for ``config.yaml``, optional ``.env``, and LLM defaults.

The pipeline defaults to **local Ollama** (see ``config.yaml`` → ``llm``).
Override via environment or edit config before running ``run.py``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from lib.paths import LLM_PIPELINE_ROOT, REPO_ROOT


class Config:
    """Immutable configuration loaded from ``config.yaml`` + optional ``.env``."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data
        self._apply_llm_defaults()

    @property
    def llm(self) -> dict[str, Any]:
        return self._data.get("llm", {})

    @property
    def raw(self) -> dict[str, Any]:
        return self._data

    def _apply_llm_defaults(self) -> None:
        defaults = Config._default_llm()
        llm = self._data.setdefault("llm", {})
        for key in ("provider", "model", "base_url"):
            llm.setdefault(key, defaults[key])

    @staticmethod
    def _default_llm() -> dict[str, Any]:
        return {
            "provider": "ollama",
            "model": "llama3.1:latest",
            "base_url": "http://localhost:11434/v1",
        }

    @staticmethod
    def _load_env(repo_root: Path) -> None:
        env_path = repo_root / ".env"
        if not env_path.is_file():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load YAML config and merge optional ``.env`` key/value pairs."""
    cfg_path = path or (LLM_PIPELINE_ROOT / "config.yaml")
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    Config._load_env(REPO_ROOT)

    # Apply LLM defaults
    defaults = Config._default_llm()
    llm = cfg.setdefault("llm", {})
    for key in ("provider", "model", "base_url"):
        llm.setdefault(key, defaults[key])

    return cfg


# Backwards-compatible helpers (used by tests)
_default_llm = Config._default_llm  # noqa: F405
_apply_llm_defaults = None  # replaced below for compat


def _apply_llm_defaults(cfg: dict[str, Any]) -> None:
    """Apply LLM defaults to a mutable config dict (legacy compat)."""
    defaults = _default_llm()
    llm = cfg.setdefault("llm", {})
    for key in ("provider", "model", "base_url"):
        llm.setdefault(key, defaults[key])
'''

# ── lib/__init__.py (public namespace) ───────────────────────────────────────

lib_init = '''\
"""Shared code for llm_pipeline and agentic/hermes.

Public namespace — import from here after Track 2 extraction:
    from lib import schema, config, paths
"""

from __future__ import annotations

# Track 2: extracted from llm_pipeline/
from lib.config import Config, _apply_llm_defaults, _default_llm, load_config  # noqa: F401
from lib.paths import (  # noqa: F401
    AGENTIC_ROOT,
    LLM_PIPELINE_ROOT,
    REPO_ROOT,
    WEB_ROOT,
)
from lib.schema import (  # noqa: F401
    Category,
    DigestDocument,
    ResourceLink,
    Story,
)

__all__ = [
    "load_config",
    "Config",
    "REPO_ROOT",
    "LLM_PIPELINE_ROOT",
    "WEB_ROOT",
    "AGENTIC_ROOT",
    "ResourceLink",
    "Story",
    "Category",
    "DigestDocument",
]
'''

# ── llm_pipeline/schema.py (deprecation shim) ───────────────────────────────

llm_schema_shim = '''\
"""Pydantic schema for Instructor / validation (matches digest JSON shape).

.. deprecated::
    Moved to ``lib.schema``. Import from there directly; this shim will be
    removed once the single-agent runtime proves parity via automated fixtures.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.schema is deprecated; use lib.schema instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.schema import (  # noqa: F401
    Category,
    CategoryStories,
    DigestDocument,
    DigestHeader,
    GapCategories,
    ResourceLink,
    Story,
    StoryEnrich,
)

__all__ = [
    "ResourceLink",
    "Story",
    "Category",
    "DigestDocument",
    "StoryEnrich",
    "CategoryStories",
    "GapCategories",
    "DigestHeader",
]
'''

# ── llm_pipeline/config.py (deprecation shim) ───────────────────────────────

llm_config_shim = '''\
"""Configuration loader for ``config.yaml``, optional ``.env``, and LLM defaults.

.. deprecated::
    Moved to ``lib.config``. Import from there directly; this shim will be
    removed once the single-agent runtime proves parity via automated fixtures.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "llm_pipeline.config is deprecated; use lib.config instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export everything from the canonical location
from lib.config import (  # noqa: F401
    Config,
    _apply_llm_defaults,
    _default_llm,
    load_config,
)

__all__ = ["load_config", "_default_llm", "_apply_llm_defaults", "Config"]
'''

# ── Write all files ─────────────────────────────────────────────────────────

files = {
    ROOT / "lib" / "schema.py": lib_schema,
    ROOT / "lib" / "config.py": lib_config,
    ROOT / "lib" / "__init__.py": lib_init,
    ROOT / "llm_pipeline" / "schema.py": llm_schema_shim,
    ROOT / "llm_pipeline" / "config.py": llm_config_shim,
}

for path, content in files.items():
    path.write_text(content, encoding="utf-8")
    print(f"  ✓ {path.relative_to(ROOT)}")

print("\nDone — all P0 extraction files written.")
