"""Build the static admin dashboard frame (served locally via admin_server)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from llm_pipeline.frame_author import inject_author_card
from llm_pipeline.frame_nav import diagnostics_available, inject_frame_nav
from llm_pipeline.site_footer import inject_site_footer
from llm_pipeline.styles import frame_styles
from lib.paths import LLM_PIPELINE_ROOT

ADMIN_DIR = LLM_PIPELINE_ROOT / "server"


def _read_admin_asset(name: str) -> str:
    return (ADMIN_DIR / name).read_text(encoding="utf-8")


def build_admin_html(cfg: dict[str, Any] | None = None) -> str:
    from llm_pipeline.config import load_config
    from llm_pipeline.paths import diagnostics_dir

    if cfg is None:
        cfg = load_config()

    theme_js = (LLM_PIPELINE_ROOT / "vendor" / "ai-news-digest" / "theme.js").read_text(encoding="utf-8")
    admin_css = _read_admin_asset("admin.css")
    admin_js = _read_admin_asset("admin-app.js")
    styles = frame_styles() + "\n" + admin_css

    html = f"""<!DOCTYPE html>
<html lang="en" data-admin-deploy="static">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Digest · Control Admin</title>
  <style>{styles}</style>
</head>
<body>
  <div class="admin-readonly-banner hidden" id="admin-readonly-banner" role="status"></div>
  <header class="admin-masthead">
    <div class="admin-masthead-inner">
      <div class="admin-brand">
        <span class="admin-brand-glyph">⎈</span>
        <div>
          <h1>Control Admin</h1>
          <p class="admin-sub">Pipeline · git · tuning · deployment precheck</p>
        </div>
      </div>
    </div>
  </header>
  <div class="admin-status-bar" id="admin-status-strip" aria-label="Admin status">
    <span class="admin-pill admin-pill-warn" id="admin-api-pill">API offline</span>
    <span class="admin-pill" id="admin-git-pill">git …</span>
    <span class="admin-pill" id="admin-precheck-pill">precheck pending</span>
  </div>
  <main class="admin-grid" id="admin-root"></main>
  <script>(function(){{var h=(location.hostname||'').toLowerCase();window.__ADMIN_READONLY__=h.endsWith('.github.io');window.__ADMIN_API__='';}})();</script>
  <script>{theme_js}</script>
  <script>{admin_js}</script>
</body>
</html>
"""
    diag_ok = diagnostics_available(cfg, diagnostics_dir(cfg))
    html = inject_frame_nav(
        html,
        "admin",
        diagnostics_available=diag_ok,
        admin_available=False,
    )
    html = inject_author_card(html, cfg)
    return inject_site_footer(html, cfg)


def rebuild_admin_archive(cfg: dict[str, Any] | None = None, admin: Path | None = None) -> Path:
    from pipeline.config import load_config

    if cfg is None:
        cfg = load_config()
    if admin is None:
        admin = ADMIN_DIR
    admin.mkdir(parents=True, exist_ok=True)
    html = build_admin_html(cfg)
    out = admin / "index.html"
    out.write_text(html, encoding="utf-8")
    meta = {
        "schema": "aidigest.admin/v1",
        "updated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    (admin / "index.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"  OK admin archive {out}")
    return out


def assert_admin_html_ready(html: str) -> None:
    if "admin-grid" not in html or "Control Admin" not in html:
        raise RuntimeError("admin index.html failed sanity check")
