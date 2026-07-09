#!/usr/bin/env python3
"""
Agentic Hermes admin — profiles, Ollama, kanban, .runtime lifecycle.

Usage:
    python agentic/hermes/admin/manage.py bootstrap [--skip-setup]
    python agentic/hermes/admin/manage.py setup [--dry-run]
    python agentic/hermes/admin/manage.py nuke [--yes]
    python agentic/hermes/admin/manage.py status
    python agentic/hermes/admin/manage.py hermes [--] <hermes-cli-args...>

Pipeline lifecycle (venv, cache, digest runs): ``python admin/manage.py``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[3]
HERMES_PKG = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(HERMES_PKG) not in sys.path:
    sys.path.insert(0, str(HERMES_PKG))

from tools.artifacts import (  # noqa: E402
    DIGEST_ARTIFACT,
    LIBRARIAN_ARTIFACT,
    load_digest_from_synthesizer_workspace,
    validate_librarian_artifact,
    validate_researcher_artifact,
    validate_synthesizer_artifact,
)
from tools.profiles import (  # noqa: E402
    CONCIERGE,
    DEPRECATED_PROFILES,
    LEGACY,
    LIBRARIAN,
    RESEARCHER,
    SYNTHESIZER,
    WORKERS,
)
from tools.runtime_store import (  # noqa: E402
    load_digest,
    persist_digest,
    persist_librarian,
    persist_research,
    run_dir,
    stage_librarian_for_workspace,
    write_manifest,
)

_GATE_ASSIGNEES = tuple(sorted(set(WORKERS) | set(LEGACY.keys())))
CONFIG_DIR = Path(__file__).resolve().parent / "config"
MANIFEST_PATH = CONFIG_DIR / "manifest.yaml"
ROLES_PATH = CONFIG_DIR / "hermes_roles.yaml"
SOULS_DIR = CONFIG_DIR / "souls"
RUNTIME = HERMES_PKG / ".runtime"
HERMES_HOME = Path.home() / ".hermes"
_KANBAN_GOAL_QUIET_MARKER = "# AI Digest: goal-mode workers need --quiet for Ralph loop"
_KANBAN_SPAWN_OLD = '''    cmd.extend([
        "chat",
        "-q", prompt,
    ])'''
_KANBAN_SPAWN_NEW = f'''    {_KANBAN_GOAL_QUIET_MARKER} (cli.py quiet path).
    _chat_args: list[str] = ["chat", "-q", prompt]
    if task.goal_mode:
        _chat_args.insert(1, "--quiet")
    cmd.extend(_chat_args)'''


_CLI_GOAL_LOOP_MARKER = "# AI Digest: goal loop on chat -q path"
_CLI_GOAL_LOOP_OLD = """                cli._show_security_advisories()
                cli.chat(query, images=single_query_images or None)
                cli._print_exit_summary()"""
_CLI_GOAL_LOOP_NEW = f"""                cli._show_security_advisories()
                _kanban_first_response = cli.chat(query, images=single_query_images or None) or ""
                # {_CLI_GOAL_LOOP_MARKER} (dashboard / non-quiet dispatchers).
                if os.environ.get("HERMES_KANBAN_GOAL_MODE") == "1":
                    try:
                        _run_kanban_goal_loop_q(cli, _kanban_first_response)
                    except Exception as _goal_exc:
                        logger.debug("kanban goal loop failed: %s", _goal_exc)
                cli._print_exit_summary()"""

_TOOLSETS_DIGEST_MARKER = "# AI Digest: digest + kanban_worker toolsets"
_TOOLSETS_KANBAN_WORKER_INSERT = f'''        "includes": [],
    }},

    {_TOOLSETS_DIGEST_MARKER}
    "kanban_worker": {{
        "description": "AI Digest leaf kanban worker — show/complete/block only",
        "tools": [
            "kanban_show", "kanban_complete", "kanban_block",
            "kanban_heartbeat", "kanban_comment",
        ],
        "includes": [],
    }},

    "digest": {{
        "description": "AI Digest researcher ingest tools (digest-tools plugin)",
        "tools": ["verify_url", "fetch_rss", "read_preflight_category", "read_crawl_markdown", "read_structured_json", "read_topic_config", "synthesize_digest"],
        "includes": [],
    }},

    "digest_admin": {{
        "description": "AI Digest Concierge orchestration — board status and GO",
        "tools": ["digest_board_status", "digest_setup_board", "digest_go"],
        "includes": [],
    }},

    "discord": {{'''
_TOOLSETS_KANBAN_ANCHOR = '''        "includes": [],
    },

    "discord": {'''

# Minimal worker surface — no hermes-cli (re-expands clarify, browser, …).
_RESEARCHER_CLI_TOOLSETS = ["file", "web", "kanban_worker", "digest", "terminal"]
_SYNTHESIZER_CLI_TOOLSETS = ["file", "kanban_worker", "digest"]

_KANBAN_COMPLETE_ARTIFACT_MARKER = "# AI Digest: researcher output.md artifact gate"
_KANBAN_ROLE_GATES_MARKER = "# AI Digest: role artifact gates (orio_* workers)"
_KANBAN_JUDGE_GOAL_MARKER = "# AI Digest: judge_goal 4-tuple unpack"
_KANBAN_JUDGE_GOAL_OLD = "                    verdict, reason, _ = judge_goal("
_KANBAN_JUDGE_GOAL_NEW = (
    "                    # " + _KANBAN_JUDGE_GOAL_MARKER + "\n"
    "                    verdict, reason, _, _ = judge_goal("
)
_KANBAN_COMPLETE_ANCHOR = """            try:
                ok = kb.complete_task("""
_KANBAN_ROLE_GATES_BLOCK = """            # """ + _KANBAN_ROLE_GATES_MARKER + """
            if task and (task.assignee or "").lower() in """ + repr(_GATE_ASSIGNEES) + """:
                import json as _json
                import re as _re
                from pathlib import Path as _Path
                _assignee = (task.assignee or "").lower()
                _ws = task.workspace_path or str(
                    _Path.home() / ".hermes" / "kanban" / "workspaces" / tid
                )
                _errs: list[str] = []
                if _assignee in ("researcher", "ai_news_researcher", "orio_researcher"):
                    _path = _Path(_ws) / "output.md"
                    if not _path.is_file():
                        _errs.append(f"missing {_path}")
                    else:
                        _text = _path.read_text(encoding="utf-8")
                        if len(_text.strip()) < 40:
                            _errs.append("output.md too short")
                        if len(_re.findall(r"https?://", _text)) < 2:
                            _errs.append("output.md needs at least 2 URLs")
                        if len([ln for ln in _text.splitlines() if ln.strip().startswith("-")]) < 3:
                            _errs.append("output.md needs at least 3 bullet lines")
                    if _errs:
                        return tool_error(
                            "kanban_complete blocked: researcher output.md invalid — "
                            + "; ".join(_errs)
                            + ". Write output.md with verified URLs via your tools, then retry kanban_complete "
                            f'with artifacts: ["{_Path(_ws) / "output.md"}"]'
                        )
                elif _assignee in ("librarian", "ai_news_librarian", "orio_librarian"):
                    _path = _Path(_ws) / "librarian.md"
                    if not _path.is_file():
                        _errs.append(f"missing {_path}")
                    else:
                        _text = _path.read_text(encoding="utf-8")
                        if len(_text.strip()) < 80:
                            _errs.append("librarian.md too short")
                        if _text.count("##") < 2:
                            _errs.append("librarian.md needs section headings")
                        if len(_re.findall(r"https?://", _text)) < 2:
                            _errs.append("librarian.md needs at least 2 URLs")
                    if _errs:
                        return tool_error(
                            "kanban_complete blocked: librarian.md invalid — "
                            + "; ".join(_errs)
                            + ". Write librarian.md in your workspace, then retry kanban_complete "
                            f'with artifacts: ["{_path}"]'
                        )
                elif _assignee in ("synthesizer", "ai_news_synthesizer", "orio_synthesizer"):
                    _path = _Path(_ws) / "digest.json"
                    if not _path.is_file():
                        _errs.append(f"missing {_path}")
                    else:
                        try:
                            _data = _json.loads(_path.read_text(encoding="utf-8"))
                        except _json.JSONDecodeError as _exc:
                            _errs.append(f"digest.json invalid JSON: {_exc}")
                        else:
                            if not str(_data.get("summary") or "").strip():
                                _errs.append("digest.json missing summary")
                            _cats = _data.get("categories")
                            if not isinstance(_cats, list) or not _cats:
                                _errs.append("digest.json needs categories[]")
                            elif len(_cats) < 12:
                                _errs.append(f"digest.json needs 12 categories, got {len(_cats)}")
                            else:
                                _stories = sum(
                                    len(c.get("stories") or [])
                                    for c in _cats
                                    if isinstance(c, dict)
                                )
                                if _stories < 20:
                                    _errs.append(
                                        f"digest.json needs at least 20 stories, got {_stories}"
                                    )
                    if _errs:
                        return tool_error(
                            "kanban_complete blocked: synthesizer digest.json invalid — "
                            + "; ".join(_errs)
                            + ". Write digest.json (12 categories, ≥20 stories) in your workspace, "
                            "then retry kanban_complete "
                            f'with artifacts: ["{_path}"]'
                        )

            try:
                ok = kb.complete_task("""
_KANBAN_COMPLETE_INSERT = _KANBAN_ROLE_GATES_BLOCK


def _hermes_agent_root() -> Path | None:
    """Locate upstream hermes-agent (kanban_db.py lives under hermes_cli/)."""
    candidates: list[Path] = []
    hermes_bin = _hermes_bin()
    if hermes_bin:
        p = Path(hermes_bin).resolve()
        for parent in (p.parent.parent, p.parent.parent.parent):
            candidates.append(parent)
    candidates.append(Path.home() / ".hermes" / "hermes-agent")
    for root in candidates:
        if (root / "hermes_cli" / "kanban_db.py").is_file():
            return root
    return None


_CLI_PLUGIN_DISCOVER_MARKER = "# AI Digest: re-discover plugins for kanban workers"
_CLI_PLUGIN_DISCOVER_ANCHOR = "        wait_for_mcp_discovery()\n"
_CLI_PLUGIN_DISCOVER_INSERT = f"""        wait_for_mcp_discovery()

        # {_CLI_PLUGIN_DISCOVER_MARKER}
        import os
        if os.environ.get("HERMES_KANBAN_TASK"):
            try:
                from hermes_cli.plugins import discover_plugins
                from model_tools import _clear_tool_defs_cache

                discover_plugins(force=True)
                _clear_tool_defs_cache()
            except Exception as _plugin_exc:
                logger.debug(
                    "kanban worker plugin re-discovery skipped: %s", _plugin_exc
                )

"""


def _ensure_hermes_worker_plugin_discover_patch(*, dry_run: bool = False) -> None:
    """Re-run plugin discovery before kanban worker agent init.

    ``model_tools`` may import and call ``discover_plugins()`` before profile-
    scoped ``HERMES_HOME`` and ``$HERMES_HOME/plugins/`` are fully visible.
    Workers then lose digest-tools (``synthesize_digest``) even when setup
    symlinked the plugin into the assignee profile.
    """
    root = _hermes_agent_root()
    if root is None:
        return
    target = root / "hermes_cli" / "cli_agent_setup_mixin.py"
    if not target.is_file():
        print("  WARN cli_agent_setup_mixin.py not found — plugin discover patch not applied")
        return
    text = target.read_text(encoding="utf-8")
    if _CLI_PLUGIN_DISCOVER_MARKER in text:
        if not dry_run:
            print("  ✓ cli_agent_setup_mixin kanban plugin re-discover (already applied)")
        return
    if _CLI_PLUGIN_DISCOVER_ANCHOR not in text:
        print("  WARN cli_agent_setup_mixin wait_for_mcp_discovery anchor changed — patch not applied")
        return
    if dry_run:
        print(f"  would patch {target} (kanban worker plugin re-discover)")
        return
    target.write_text(text.replace(_CLI_PLUGIN_DISCOVER_ANCHOR, _CLI_PLUGIN_DISCOVER_INSERT), encoding="utf-8")
    print(f"  ✓ patched {target.name} (kanban worker plugin re-discover)")


def _ensure_hermes_kanban_goal_quiet_patch(*, dry_run: bool = False) -> None:
    """Patch kanban worker spawn so goal_mode tasks pass ``--quiet``.

    Upstream Hermes runs the Ralph goal loop only on cli.py's ``quiet`` path
    (``-Q`` / ``--quiet``), but the dispatcher spawns workers with ``-q``
    (query) only — so ``--goal`` cards never enter the loop and exit rc=0.
    """
    root = _hermes_agent_root()
    if root is None:
        print("  WARN hermes-agent root not found — skip goal-mode spawn patch")
        return
    target = root / "hermes_cli" / "kanban_db.py"
    text = target.read_text(encoding="utf-8")
    if _KANBAN_GOAL_QUIET_MARKER in text:
        if not dry_run:
            print("  ✓ kanban goal-mode spawn patch (already applied)")
        return
    if _KANBAN_SPAWN_OLD not in text:
        print(
            "  WARN kanban_db.py spawn block changed upstream — "
            "goal-mode patch not applied; file an issue or patch manually"
        )
        return
    if dry_run:
        print(f"  would patch {target} (goal-mode → chat --quiet -q …)")
        return
    target.write_text(text.replace(_KANBAN_SPAWN_OLD, _KANBAN_SPAWN_NEW), encoding="utf-8")
    print(f"  ✓ patched {target.name} (goal-mode workers now use --quiet)")


def _ensure_hermes_cli_goal_loop_patch(*, dry_run: bool = False) -> None:
    """Patch cli.py so goal loop runs on ``chat -q`` (not only ``--quiet``).

    The web dashboard keeps a long-lived process; without this patch, a
    dashboard started before ``kanban_db`` spawn fix still dispatches workers
    that never enter the Ralph loop.
    """
    root = _hermes_agent_root()
    if root is None:
        print("  WARN hermes-agent root not found — skip cli goal-loop patch")
        return
    target = root / "cli.py"
    text = target.read_text(encoding="utf-8")
    if _CLI_GOAL_LOOP_MARKER in text:
        if not dry_run:
            print("  ✓ cli.py goal-loop patch (already applied)")
        return
    if _CLI_GOAL_LOOP_OLD not in text:
        print(
            "  WARN cli.py single-query block changed upstream — "
            "goal-loop patch not applied"
        )
        return
    if dry_run:
        print(f"  would patch {target} (goal loop after chat -q)")
        return
    target.write_text(text.replace(_CLI_GOAL_LOOP_OLD, _CLI_GOAL_LOOP_NEW), encoding="utf-8")
    print(f"  ✓ patched {target.name} (goal loop on chat -q path)")


def _ensure_hermes_digest_toolsets_patch(*, dry_run: bool = False) -> None:
    """Register ``kanban_worker`` and ``digest`` in upstream ``toolsets.py``.

    Plugin-only toolsets are unknown at CLI init unless present in TOOLSETS;
    without this, researcher workers lose ``kanban_complete`` entirely.
    """
    root = _hermes_agent_root()
    if root is None:
        print("  WARN hermes-agent root not found — skip toolsets patch")
        return
    target = root / "toolsets.py"
    text = target.read_text(encoding="utf-8")
    if _TOOLSETS_DIGEST_MARKER in text:
        if not dry_run:
            print("  ✓ toolsets.py digest/kanban_worker patch (already applied)")
        return
    if _TOOLSETS_KANBAN_ANCHOR not in text:
        print("  WARN toolsets.py kanban/discord anchor changed — patch not applied")
        return
    if dry_run:
        print(f"  would patch {target} (kanban_worker + digest toolsets)")
        return
    target.write_text(
        text.replace(_TOOLSETS_KANBAN_ANCHOR, _TOOLSETS_KANBAN_WORKER_INSERT),
        encoding="utf-8",
    )
    print(f"  ✓ patched {target.name} (kanban_worker + digest toolsets)")


def _ensure_hermes_kanban_complete_artifact_patch(*, dry_run: bool = False) -> None:
    """Reject kanban_complete when role artifacts fail the gate (researcher/librarian/synthesizer)."""
    root = _hermes_agent_root()
    if root is None:
        print("  WARN hermes-agent root not found — skip kanban_complete artifact patch")
        return
    target = root / "tools" / "kanban_tools.py"
    if not target.is_file():
        print("  WARN kanban_tools.py not found — skip artifact patch")
        return
    text = target.read_text(encoding="utf-8")
    if _KANBAN_ROLE_GATES_MARKER in text:
        if not dry_run:
            print("  ✓ kanban_complete role artifact gates (already applied)")
        return
    old_start = "            # # AI Digest: researcher output.md artifact gate"
    if old_start in text:
        anchor = "\n            try:\n                ok = kb.complete_task("
        start = text.find(old_start)
        end = text.find(anchor, start)
        if end < 0:
            print("  WARN kanban_tools.py role-gate anchor missing — patch not applied")
            return
        new_text = text[:start] + _KANBAN_ROLE_GATES_BLOCK + text[end + len(anchor) :]
        if dry_run:
            print(f"  would upgrade {target} (researcher → full role artifact gates)")
            return
        target.write_text(new_text, encoding="utf-8")
        print(f"  ✓ upgraded {target.name} (role artifact gates on kanban_complete)")
        return
    if _KANBAN_COMPLETE_ANCHOR not in text:
        print("  WARN kanban_tools.py complete_task anchor changed — artifact patch not applied")
        return
    if dry_run:
        print(f"  would patch {target} (role artifact gates on kanban_complete)")
        return
    target.write_text(text.replace(_KANBAN_COMPLETE_ANCHOR, _KANBAN_COMPLETE_INSERT), encoding="utf-8")
    print(f"  ✓ patched {target.name} (role artifact gates on kanban_complete)")


def _ensure_hermes_judge_goal_unpack_patch(*, dry_run: bool = False) -> None:
    """Fix goal judge unpack (judge_goal returns 4 values; old patch expected 3)."""
    root = _hermes_agent_root()
    if root is None:
        return
    target = root / "tools" / "kanban_tools.py"
    if not target.is_file():
        return
    text = target.read_text(encoding="utf-8")
    if _KANBAN_JUDGE_GOAL_MARKER in text:
        if not dry_run:
            print("  ✓ kanban_complete judge_goal unpack (already applied)")
        return
    if _KANBAN_JUDGE_GOAL_OLD not in text:
        if not dry_run:
            print("  WARN kanban_tools.py judge_goal line changed — unpack patch not applied")
        return
    if dry_run:
        print(f"  would patch {target} (judge_goal 4-tuple unpack)")
        return
    target.write_text(text.replace(_KANBAN_JUDGE_GOAL_OLD, _KANBAN_JUDGE_GOAL_NEW), encoding="utf-8")
    print(f"  ✓ patched {target.name} (judge_goal 4-tuple unpack)")


def _refresh_kanban_complete_error_message(*, dry_run: bool = False) -> None:
    """Fix stale 'Call research_topic first' text on already-patched installs."""
    root = _hermes_agent_root()
    if root is None:
        return
    target = root / "tools" / "kanban_tools.py"
    if not target.is_file():
        return
    text = target.read_text(encoding="utf-8")
    stale = ". Call research_topic first, then retry kanban_complete "
    fixed = ". Write output.md with verified URLs via your tools, then retry kanban_complete "
    if stale not in text:
        if _KANBAN_COMPLETE_ARTIFACT_MARKER in text and not dry_run:
            print("  ✓ kanban_complete error message (already current)")
        return
    if dry_run:
        print("  would refresh kanban_complete error message in kanban_tools.py")
        return
    target.write_text(text.replace(stale, fixed), encoding="utf-8")
    print("  ✓ refreshed kanban_complete error message in kanban_tools.py")


def _ensure_digest_admin_toolset_tools(*, dry_run: bool = False) -> None:
    """Ensure digest_admin toolset lists Concierge orchestration tools."""
    root = _hermes_agent_root()
    if root is None:
        return
    target = root / "toolsets.py"
    if not target.is_file():
        return
    text = target.read_text(encoding="utf-8")
    want = (
        '"digest_admin": {\n'
        '        "description": "AI Digest Concierge orchestration — board status and GO",\n'
        '        "tools": ["digest_board_status", "digest_setup_board", "digest_go"],\n'
        '        "includes": [],\n'
        "    },"
    )
    if want in text:
        if not dry_run:
            print("  ✓ toolsets.py digest_admin (already present)")
        return
    anchor = '"discord": {'
    if anchor not in text:
        print("  WARN toolsets.py discord anchor missing — digest_admin not applied")
        return
    insert = want + "\n\n    " + anchor
    if dry_run:
        print(f"  would add digest_admin toolset to {target}")
        return
    target.write_text(text.replace(anchor, insert, 1), encoding="utf-8")
    print(f"  ✓ added digest_admin toolset to {target.name}")


def _refresh_kanban_role_gate_block(*, dry_run: bool = False) -> None:
    """Upgrade kanban artifact gates when profile names change (orio_*)."""
    root = _hermes_agent_root()
    if root is None:
        return
    target = root / "tools" / "kanban_tools.py"
    if not target.is_file():
        return
    text = target.read_text(encoding="utf-8")
    if _KANBAN_ROLE_GATES_MARKER in text:
        return
    old_markers = (
        "# AI Digest: role artifact gates (researcher / librarian / synthesizer)",
        "# AI Digest: role artifact gates (orio_* workers)",
        "# AI Digest: role artifact gates (ai_news_* workers)",
    )
    start = -1
    for marker in old_markers:
        idx = text.find(marker)
        if idx >= 0:
            start = text.rfind("\n            # ", 0, idx)
            if start < 0:
                start = text.find("            # ", idx - 20)
            break
    if start < 0:
        return
    anchor = "\n            try:\n                ok = kb.complete_task("
    end = text.find(anchor, start)
    if end < 0:
        return
    new_text = text[:start] + "\n" + _KANBAN_ROLE_GATES_BLOCK + text[end + len(anchor) :]
    if dry_run:
        print(f"  would refresh kanban role gates in {target}")
        return
    target.write_text(new_text, encoding="utf-8")
    print(f"  ✓ refreshed {target.name} role artifact gates (orio_* profiles)")


def _ensure_digest_toolset_tools(*, dry_run: bool = False) -> None:
    """Ensure digest toolset lists ingest tools on already-patched installs."""
    root = _hermes_agent_root()
    if root is None:
        return
    target = root / "toolsets.py"
    text = target.read_text(encoding="utf-8")
    want = (
        '"tools": ["verify_url", "fetch_rss", "read_preflight_category", '
        '"read_crawl_markdown", "read_structured_json", "read_topic_config", "synthesize_digest"],'
    )
    legacy = '"tools": ["verify_url", "fetch_rss", "read_preflight_category", "read_crawl_markdown", "read_structured_json", "read_topic_config"],'
    if want in text:
        if not dry_run:
            print("  ✓ toolsets.py digest tools (already present)")
        return
    if legacy in text:
        text = text.replace(legacy, want)
        if not dry_run:
            target.write_text(text, encoding="utf-8")
            print("  ✓ updated digest tools in toolsets.py")
        elif dry_run:
            print("  would update digest tools in toolsets.py")
        return
    for old in (
        '"tools": ["verify_url", "research_topic"],',
        '"tools": ["verify_url"],',
    ):
        if old in text:
            if dry_run:
                print(f"  would update digest tools in {target}")
                return
            target.write_text(text.replace(old, want, 1), encoding="utf-8")
            print(f"  ✓ updated digest tools in {target.name}")
            return
    print("  WARN toolsets.py digest tools list changed — update manually")


def _ensure_digest_plugin_symlink(*, dry_run: bool = False) -> None:
    """Symlink digest-tools plugin into ~/.hermes/plugins/."""
    dest = HERMES_HOME / "plugins" / "digest-tools"
    src = HERMES_PKG / "plugins" / "digest-tools"
    if dest.is_symlink() and dest.resolve() == src.resolve():
        if not dry_run:
            print("  ✓ digest-tools plugin symlink")
        return
    if dry_run:
        print(f"  would symlink {dest} → {src}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    dest.symlink_to(src)
    print(f"  ✓ digest-tools plugin → {src.relative_to(REPO)}")


def _ensure_digest_plugin_enabled(*, dry_run: bool = False) -> None:
    """Enable digest-tools plugin (required for synthesize_digest in workers)."""
    print("== setup: digest-tools plugin ==")
    if dry_run:
        print("  would hermes plugins enable digest-tools")
        return
    proc = subprocess.run(
        [_hermes_bin() or "hermes", "plugins", "enable", "digest-tools"],
        input="n\n",
        text=True,
        capture_output=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 and "enabled" not in out.lower():
        print(out.strip() or f"  WARN plugins enable failed (exit {proc.returncode})")
        return
    print("  ✓ digest-tools plugin enabled")


def _configure_concierge_toolsets(*, dry_run: bool = False) -> None:
    """Pin Concierge to kanban + digest_admin orchestration tools."""
    spec = _load_roles()
    toolsets = list(spec.get("concierge_toolsets") or ["file", "kanban", "digest_admin"])
    print("== setup: concierge tool surface ==")
    cfg_path = _profile_dir(CONCIERGE) / "config.yaml"
    if dry_run:
        print(f"  would set {cfg_path} toolsets = {toolsets}")
        return
    if not cfg_path.is_file():
        print(f"  WARN skip — {cfg_path} missing")
        return
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg["toolsets"] = toolsets
    pt = cfg.setdefault("platform_toolsets", {})
    pt["cli"] = toolsets
    agent = cfg.setdefault("agent", {})
    disabled = set(agent.get("disabled_toolsets") or [])
    disabled.update(["browser", "delegation", "cronjob", "code_execution"])
    agent["disabled_toolsets"] = sorted(disabled)
    with cfg_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)
    print(f"  ✓ {CONCIERGE} toolsets {toolsets}")


def _configure_researcher_worker_toolsets(*, dry_run: bool) -> None:
    """Pin researcher workers to a small tool surface.

    ``hermes config set toolsets …`` stores nested lists as JSON strings;
    Hermes then ignores them and falls back to the full ``hermes-cli`` bundle
    (clarify, kanban_create, browser, …). Write profile YAML directly.
    """
    print("== setup: researcher worker tool surface ==")
    cfg_path = _profile_dir(RESEARCHER) / "config.yaml"
    toolsets = list(_RESEARCHER_CLI_TOOLSETS)
    if dry_run:
        print(f"  would set {cfg_path} toolsets + platform_toolsets.cli = {toolsets}")
        return
    if not cfg_path.is_file():
        print(f"  WARN skip — {cfg_path} missing")
        return
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg["toolsets"] = toolsets
    pt = cfg.setdefault("platform_toolsets", {})
    pt["cli"] = toolsets
    agent = cfg.setdefault("agent", {})
    disabled = set(agent.get("disabled_toolsets") or [])
    disabled.update(["clarify", "skills", "browser", "delegation", "cronjob", "digest_admin"])
    agent["disabled_toolsets"] = sorted(disabled)
    with cfg_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)
    print(f"  ✓ {RESEARCHER} toolsets + platform_toolsets.cli {toolsets}")


def _configure_synthesizer_worker_toolsets(*, dry_run: bool = False) -> None:
    """Pin synthesizer workers to file + kanban + synthesize_digest."""
    print("== setup: synthesizer worker tool surface ==")
    cfg_path = _profile_dir(SYNTHESIZER) / "config.yaml"
    toolsets = list(_SYNTHESIZER_CLI_TOOLSETS)
    if dry_run:
        print(f"  would set {cfg_path} toolsets + platform_toolsets.cli = {toolsets}")
        return
    if not cfg_path.is_file():
        print(f"  WARN skip — {cfg_path} missing")
        return
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    cfg["toolsets"] = toolsets
    pt = cfg.setdefault("platform_toolsets", {})
    pt["cli"] = toolsets
    agent = cfg.setdefault("agent", {})
    disabled = set(agent.get("disabled_toolsets") or [])
    disabled.update(["clarify", "skills", "browser", "delegation", "cronjob", "web", "terminal", "code_execution", "digest_admin"])
    agent["disabled_toolsets"] = sorted(disabled)
    with cfg_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)
    print(f"  ✓ {SYNTHESIZER} toolsets + platform_toolsets.cli {toolsets}")


def _remove_legacy_profiles(*, dry_run: bool = False) -> None:
    """Drop pre-rename Hermes profiles (concierge, ai_news_*, …)."""
    current = {r["name"] for r in (_load_roles().get("roles") or []) if r.get("name")}
    print("== setup: legacy profile cleanup ==")
    for old in DEPRECATED_PROFILES:
        if old in current:
            continue
        if not _profile_dir(old).is_dir():
            continue
        if dry_run:
            print(f"  would hermes profile delete {old}")
            continue
        proc = _run_hermes("profile", "delete", old, "-y")
        if proc.returncode == 0:
            print(f"  ✓ removed legacy profile {old}")
        else:
            print(f"  WARN could not remove {old}: {(proc.stderr or proc.stdout).strip()}")


def _configure_worker_profile_plugins(
    profile_names: list[str],
    *,
    dry_run: bool = False,
) -> None:
    """Mirror root ``plugins.enabled`` and symlink user plugins into worker profiles.

    Kanban dispatch sets ``HERMES_HOME`` to the assignee profile directory.
    Profile-scoped ``load_config()`` does not inherit root plugin enablement,
    and ``discover_plugins()`` scans ``$HERMES_HOME/plugins/`` — not the root
    ``~/.hermes/plugins/`` tree — so digest-tools never registers and
    ``synthesize_digest`` is absent from the worker tool schema unless we
    copy the allow-list and link the plugin here.
    """
    print("== setup: worker profile plugins ==")
    root_cfg_path = HERMES_HOME / "config.yaml"
    plugin_src = HERMES_HOME / "plugins" / "digest-tools"
    if not root_cfg_path.is_file():
        print(f"  WARN skip — {root_cfg_path} missing")
        return
    if not plugin_src.is_dir():
        print(f"  WARN skip — {plugin_src} missing (run digest-tools symlink step)")
        return
    with root_cfg_path.open(encoding="utf-8") as f:
        root_cfg = yaml.safe_load(f) or {}
    root_plugins = root_cfg.get("plugins")
    if not isinstance(root_plugins, dict) or not root_plugins.get("enabled"):
        print("  WARN root plugins.enabled empty — run plugins enable digest-tools first")
        return
    for name in profile_names:
        cfg_path = _profile_dir(name) / "config.yaml"
        plugin_dest_dir = _profile_dir(name) / "plugins"
        plugin_dest = plugin_dest_dir / "digest-tools"
        if not cfg_path.is_file():
            print(f"  WARN skip — {cfg_path} missing")
            continue
        if dry_run:
            print(f"  would copy plugins.enabled + symlink digest-tools → {name}")
            continue
        with cfg_path.open(encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        cfg["plugins"] = {
            "enabled": list(root_plugins.get("enabled") or []),
            "disabled": list(root_plugins.get("disabled") or []),
            "entries": dict(root_plugins.get("entries") or {}),
        }
        with cfg_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(cfg, f, default_flow_style=False, sort_keys=False)
        plugin_dest_dir.mkdir(parents=True, exist_ok=True)
        if plugin_dest.is_symlink() or plugin_dest.is_dir():
            if plugin_dest.resolve() != plugin_src.resolve():
                if plugin_dest.is_symlink():
                    plugin_dest.unlink()
                else:
                    print(f"  WARN {plugin_dest} exists and is not digest-tools — skip link")
                    continue
        if not plugin_dest.exists():
            plugin_dest.symlink_to(plugin_src)
        print(f"  ✓ {name} plugins.enabled + digest-tools symlink")


def _load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_roles() -> dict[str, Any]:
    if not ROLES_PATH.is_file():
        print(f"ERROR missing {ROLES_PATH.relative_to(REPO)}")
        sys.exit(1)
    with ROLES_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _hermes_bin() -> str | None:
    return shutil.which("hermes")


def _run_hermes(
    *argv: str,
    profile: str | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    hermes = _hermes_bin()
    if not hermes:
        raise RuntimeError("hermes not on PATH")
    cmd = [hermes]
    if profile:
        cmd.extend(["-p", profile])
    cmd.extend(argv)
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, check=check)


def _repo_llm_config() -> dict[str, Any]:
    cfg_path = REPO / "config.yaml"
    if not cfg_path.is_file():
        return {}
    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg.get("llm") or {}


def _ollama_models() -> set[str]:
    if not shutil.which("ollama"):
        return set()
    proc = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if proc.returncode != 0:
        return set()
    names: set[str] = set()
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if parts:
            names.add(parts[0])
    return names


def _resolve_model(requested: str, fallback: str, installed: set[str]) -> str:
    if not installed or requested in installed:
        return requested
    if fallback in installed:
        print(f"  WARN model {requested!r} not in ollama list — using {fallback!r}")
        return fallback
    print(f"  WARN model {requested!r} not installed — using {fallback!r} anyway")
    return fallback


def _profile_dir(name: str) -> Path:
    return HERMES_HOME / "profiles" / name


def _profile_model_config(
    profile: str,
    model: str,
    provider: str,
    base_url: str,
    context_length: str,
    *,
    dry_run: bool,
) -> None:
    for key, value in (
        ("model.default", model),
        ("model.provider", provider),
        ("model.base_url", base_url),
        ("model.context_length", context_length),
    ):
        if dry_run:
            print(f"  would hermes -p {profile} config set {key} {value}")
            continue
        proc = _run_hermes("config", "set", key, value, profile=profile)
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout)
            sys.exit(proc.returncode)


def _ensure_profile(
    name: str,
    description: str,
    *,
    dry_run: bool,
    clone_from: str = "default",
) -> None:
    if _profile_dir(name).is_dir():
        if dry_run:
            print(f"  would update {name} description")
            return
        proc = _run_hermes("profile", "describe", name, "--text", description)
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout)
            sys.exit(proc.returncode)
        print(f"  ✓ profile {name} (updated description)")
        return
    if dry_run:
        print(f"  would create profile {name}")
        return
    proc = _run_hermes(
        "profile",
        "create",
        name,
        "--clone-from",
        clone_from,
        "--description",
        description,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        sys.exit(proc.returncode)
    print(f"  ✓ profile {name} (created)")


def _deploy_soul(name: str, *, dry_run: bool) -> None:
    src = SOULS_DIR / f"{name}.md"
    if not src.is_file():
        return
    dest = _profile_dir(name) / "SOUL.md"
    if dry_run:
        print(f"  would deploy SOUL.md for {name} ← {src.relative_to(REPO)}")
        return
    if not _profile_dir(name).is_dir():
        print(f"  WARN skip SOUL for {name} — profile dir missing")
        return
    shutil.copy2(src, dest)
    print(f"  ✓ SOUL.md → {name}")


def _configure_default_ollama(
    model: str,
    provider: str,
    base_url: str,
    context_length: str,
    *,
    dry_run: bool,
) -> None:
    print("== setup: default profile → Ollama ==")
    for key, value in (
        ("model.default", model),
        ("model.provider", provider),
        ("model.base_url", base_url),
        ("model.context_length", context_length),
    ):
        if dry_run:
            print(f"  would hermes config set {key} {value}")
            continue
        proc = _run_hermes("config", "set", key, value)
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout)
            sys.exit(proc.returncode)
    if not dry_run:
        print(f"  ✓ default → {model} @ {base_url} (ctx {context_length})")


def _configure_toolsets(toolsets: list[str], *, dry_run: bool) -> None:
    payload = json.dumps(toolsets)
    print("== setup: kanban toolset ==")
    if dry_run:
        print(f"  would hermes config set toolsets {payload}")
        return
    proc = _run_hermes("config", "set", "toolsets", payload)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        sys.exit(proc.returncode)
    print(f"  ✓ toolsets {payload}")


def _configure_profile_toolsets(profile: str, toolsets: list[str], *, dry_run: bool) -> None:
    payload = json.dumps(toolsets)
    if dry_run:
        print(f"  would hermes -p {profile} config set toolsets {payload}")
        return
    proc = _run_hermes("config", "set", "toolsets", payload, profile=profile)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        sys.exit(proc.returncode)
    print(f"  ✓ {profile} toolsets {payload}")


def _configure_kanban_poc(*, dry_run: bool) -> None:
    """POC defaults: one worker at a time; no auto-decompose on block/triage."""
    print("== setup: kanban POC guards ==")
    for key, value in (
        ("kanban.max_in_progress", "1"),
        ("kanban.auto_decompose", "false"),
    ):
        if dry_run:
            print(f"  would hermes config set {key} {value}")
            continue
        proc = _run_hermes("config", "set", key, value)
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout)
            sys.exit(proc.returncode)
        print(f"  ✓ {key} = {value}")


def _configure_web(*, dry_run: bool) -> None:
    print("== setup: web search (ddgs, no API key) ==")
    if dry_run:
        print("  would hermes config set web.backend ddgs")
        print("  would hermes tools post-setup ddgs")
        print("  would hermes doctor (check web line)")
        return
    proc = _run_hermes("config", "set", "web.backend", "ddgs")
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        sys.exit(proc.returncode)
    print("  ✓ web.backend ddgs")
    proc = _run_hermes("tools", "post-setup", "ddgs")
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        sys.exit(proc.returncode)
    print("  ✓ ddgs package (post-setup)")
    proc = _run_hermes("doctor")
    combined = (proc.stdout or "") + (proc.stderr or "")
    web_ok = any("web" in line.lower() and "✓" in line for line in combined.splitlines())
    web_warn = any("web" in line.lower() and "⚠" in line for line in combined.splitlines())
    if web_ok:
        print("  ✓ doctor: web available")
    elif web_warn:
        print("  WARN doctor: web still unavailable — check `hermes doctor`")
    else:
        print("  · doctor finished (review web status manually)")


def setup_agents(*, dry_run: bool = False, quiet: bool = False) -> int:
    if not _hermes_bin():
        if quiet:
            return 0
        print("hermes not on PATH.")
        print("Install upstream Hermes, then: python agentic/hermes/admin/manage.py setup")
        return 1

    spec = _load_roles()
    ollama = spec.get("ollama") or {}
    repo_llm = _repo_llm_config()
    provider = ollama.get("provider") or "custom"
    base_url = ollama.get("base_url") or repo_llm.get("base_url") or "http://localhost:11434/v1"
    default_model = ollama.get("default_model") or repo_llm.get("model") or "llama3.1:latest"
    context_length = str(ollama.get("context_length") or 131072)
    installed = _ollama_models()
    toolsets = spec.get("toolsets") or ["hermes-cli", "kanban"]

    if not quiet:
        print("== setup: ORIO agent profiles ==")

    _configure_default_ollama(default_model, provider, base_url, context_length, dry_run=dry_run)

    for role in spec.get("roles") or []:
        name = role["name"]
        description = (role.get("description") or "").strip()
        model = _resolve_model(role.get("model") or default_model, default_model, installed)
        if not quiet:
            print(f"\n== setup: {name} ==")
        _ensure_profile(name, description, dry_run=dry_run)
        _profile_model_config(
            name, model, provider, base_url, context_length, dry_run=dry_run
        )
        _deploy_soul(name, dry_run=dry_run)
        if not dry_run and not quiet:
            print(f"  ✓ {name} → {model}")

    researcher_toolsets = spec.get("researcher_toolsets")
    if researcher_toolsets:
        if not quiet:
            print("\n== setup: researcher toolsets ==")
        if not dry_run and not quiet:
            print(f"  (applied via worker tool surface — {researcher_toolsets})")

    _configure_toolsets(toolsets, dry_run=dry_run)
    _configure_kanban_poc(dry_run=dry_run)
    _configure_web(dry_run=dry_run)
    if not quiet:
        print("\n== setup: Hermes kanban goal-mode patch ==")
    _ensure_hermes_kanban_goal_quiet_patch(dry_run=dry_run)
    _ensure_hermes_cli_goal_loop_patch(dry_run=dry_run)
    _ensure_hermes_worker_plugin_discover_patch(dry_run=dry_run)
    _ensure_hermes_digest_toolsets_patch(dry_run=dry_run)
    _ensure_digest_toolset_tools(dry_run=dry_run)
    _ensure_digest_admin_toolset_tools(dry_run=dry_run)
    _ensure_hermes_kanban_complete_artifact_patch(dry_run=dry_run)
    _refresh_kanban_role_gate_block(dry_run=dry_run)
    _ensure_hermes_judge_goal_unpack_patch(dry_run=dry_run)
    _refresh_kanban_complete_error_message(dry_run=dry_run)
    _ensure_digest_plugin_symlink(dry_run=dry_run)
    _ensure_digest_plugin_enabled(dry_run=dry_run)
    _configure_concierge_toolsets(dry_run=dry_run)
    _configure_researcher_worker_toolsets(dry_run=dry_run)
    _configure_synthesizer_worker_toolsets(dry_run=dry_run)
    _configure_worker_profile_plugins(
        [RESEARCHER, LIBRARIAN, SYNTHESIZER, CONCIERGE],
        dry_run=dry_run,
    )
    _remove_legacy_profiles(dry_run=dry_run)
    if not quiet and not dry_run:
        print("\n  Restart long-lived Hermes processes after patches:")
        print("    hermes gateway restart")
        print("    (restart `hermes dashboard` tab if open — it caches spawn code)")

    demo = (spec.get("demo_prompt") or "").strip()
    if not quiet:
        print("\n== setup: done ==")
        print("  Chat:  python agentic/hermes/admin/manage.py hermes dashboard")
        print(f"  Concierge profile: {CONCIERGE}")
        print("  Roles: python agentic/hermes/admin/manage.py hermes profile list")
        print("  python agentic/hermes/admin/manage.py go [--fresh]")
        print("  python agentic/hermes/admin/manage.py dispatch-research --redo-invalid")
        if demo:
            print("\n  Task graph (research × N → librarian → synthesizer):")
            print(f"  {demo}")
    return 0


def _kanban_create_json(
    title: str,
    *,
    assignee: str,
    body: str,
    parents: list[str] | None = None,
    goal: bool = False,
    goal_max_turns: int | None = None,
    dry_run: bool = False,
) -> str:
    if dry_run:
        parent_note = f" parents={parents}" if parents else ""
        goal_note = " --goal" + (f" --goal-max-turns {goal_max_turns}" if goal_max_turns else "")
        if goal:
            parent_note += goal_note
        print(f"  would kanban create {title!r} assignee={assignee}{parent_note}")
        return f"t_dry_{assignee}"

    cmd = ["kanban", "create", title, "--assignee", assignee, "--body", body, "--json"]
    for parent in parents or []:
        cmd.extend(["--parent", parent])
    if goal:
        cmd.append("--goal")
    if goal_max_turns is not None:
        cmd.extend(["--goal-max-turns", str(goal_max_turns)])
    proc = _run_hermes(*cmd)
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        sys.exit(proc.returncode)
    try:
        return json.loads(proc.stdout)["id"]
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"ERROR parsing kanban create output: {exc}\n{proc.stdout}")
        sys.exit(1)


def _research_body(topic: str, *, prefix: str | None = None) -> str:
    from tools.topics import research_task_body

    pfx = prefix or "YYYYMMDDHHMMSS"
    return research_task_body(topic, prefix=pfx)


def _librarian_body(*, prefix: str | None = None) -> str:
    pfx = prefix or "YYYYMMDDHHMMSS"
    cache = f"agentic/hermes/.runtime/artifacts/{pfx}/research/"
    return (
        f"Librarian merge for AI Digest (run prefix `{pfx}`).\n\n"
        f"Read researcher outputs under `{cache}` (one .md per topic). "
        "Merge, classify, dedupe across topics; map to the standing topic list. "
        "Write **librarian.md** in your workspace (structured merge + notes for "
        "the Synthesizer). Do not fetch new URLs.\n\n"
        'Call `kanban_complete` with artifacts: ["<absolute-path>/librarian.md"]. '
        "Do not call kanban_block unless capability-blocked."
    )


def _synthesizer_body(*, prefix: str | None = None) -> str:
    pfx = prefix or "YYYYMMDDHHMMSS"
    return (
        f"Synthesize AI Digest (run prefix `{pfx}`).\n\n"
        "Tools allowed: kanban_show, read_file, synthesize_digest, kanban_complete only.\n"
        "Do NOT use terminal, patch, search_files, or Python scripts.\n\n"
        "Steps:\n"
        "1. kanban_show — workspace path + prefix from comments.\n"
        "2. read_file librarian.md in your workspace (staged before dispatch).\n"
        f"3. synthesize_digest(workspace=<workspace>, prefix={pfx}) — wait for it to finish.\n"
        "4. read_file digest.json — confirm it exists.\n"
        '5. kanban_complete with artifacts: ["<workspace>/digest.json"].\n\n'
        "Do not hand-author digest.json. Do not call kanban_complete until step 4 passes."
    )


def _archive_digest_board() -> None:
    """Archive existing digest POC tasks so GO starts clean."""
    _archive_kanban_tasks(_digest_board_rows())


def _digest_board_rows() -> list[dict[str, Any]]:
    titles = {"Librarian: merge & classify", "Synthesize digest"}
    return [
        r
        for r in _kanban_list_json()
        if str(r.get("title", "")).startswith("Research:") or str(r.get("title", "")) in titles
    ]


def _handover_board_snapshot() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _digest_board_rows():
        rows.append(
            {
                "id": str(row.get("id", "")),
                "title": str(row.get("title", "")),
                "assignee": str(row.get("assignee", "")),
                "status": str(row.get("status", "")),
            }
        )
    return rows


def _handover_chain_ok() -> tuple[bool, list[str]]:
    """All digest-graph tasks must be done before board cleanup."""
    issues: list[str] = []
    for row in _digest_board_rows():
        status = str(row.get("status", ""))
        if status != "done":
            issues.append(f"{row.get('id')} {row.get('title')} status={status} (want done)")
    return not issues, issues


def _write_handover_receipt(
    prefix: str,
    *,
    tasks: list[dict[str, str]],
    board_clear: bool,
) -> Path:
    from datetime import datetime, timezone

    from tools.handover_trace import build_handover_trace

    trace = build_handover_trace(prefix)
    receipt = {
        "prefix": prefix,
        "mode": "agent-workers",
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tasks": tasks,
        "board_clear": board_clear,
        "passed": board_clear and all(t.get("status") == "done" for t in tasks),
        "provenance": trace,
    }
    dest = RUNTIME / "artifacts" / prefix / "handover.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return dest, trace


def _archive_kanban_tasks(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        tid = row["id"]
        title = str(row.get("title", ""))
        print(f"  archive {tid} ({title})")
        _run_hermes("kanban", "archive", tid)
        _run_hermes("kanban", "archive", "--rm", tid)


def _cleanup_board_after_go() -> None:
    """Archive digest graph + agent-spawned strays so the board stays quiet."""
    titles = {"Librarian: merge & classify", "Synthesize digest"}
    stray_assignees = {"researcher-a"}
    rows = [
        r
        for r in _kanban_list_json()
        if str(r.get("title", "")).startswith("Research:")
        or str(r.get("title", "")) in titles
        or str(r.get("assignee", "")) in stray_assignees
    ]
    if not rows:
        return
    print("\n-- cleanup: archive board tasks")
    _archive_kanban_tasks(rows)


def _find_task_by_title(title: str) -> dict[str, Any] | None:
    for row in _kanban_list_json():
        if row.get("title") == title:
            return row
    return None


def _agentic_reports_dir() -> Path:
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from llm_pipeline.paths import reports_dir
    from tools.baseline import agentic_config

    return reports_dir(agentic_config())


def _research_rows() -> list[dict[str, Any]]:
    return [r for r in _kanban_list_json() if str(r.get("title", "")).startswith("Research:")]


def cmd_render_from_board(args: argparse.Namespace) -> int:
    """Phase C: validate synthesizer digest and render to agentic/hermes/reports/."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tools.baseline import agentic_config, validate_and_render

    prefix = args.prefix or _agentic_run_prefix
    digest: dict[str, Any] | None = load_digest(prefix) if prefix else None

    research = _research_rows()
    ok = sum(1 for r in research if _research_artifact_ok(r))
    if digest is None and ok == 0:
        print("ERROR no valid researcher output.md — run dispatch-research first")
        return 1

    if digest is None:
        synth = _find_task_by_title("Synthesize digest")
        if synth:
            ws = _task_workspace(_kanban_show_json(synth["id"])["task"])
            if not validate_synthesizer_artifact(ws):
                digest = load_digest_from_synthesizer_workspace(ws)
    if digest is None:
        print("ERROR no valid digest.json — synthesizer worker must complete first")
        return 1

    prefix = str(digest.get("filename_prefix") or prefix or "")
    if not prefix:
        prefix = _resolve_run_prefix(None)
        digest["filename_prefix"] = prefix

    cfg = agentic_config()
    print(f"== render-from-board: prefix={prefix} categories={len(digest.get('categories') or [])} ==")
    errors = validate_and_render(cfg, prefix, digest)
    if errors:
        print(f"  validation notes: {len(errors)} issue(s)")
        for err in errors[:5]:
            print(f"    - {err}")
    html = _agentic_reports_dir() / f"{prefix}.html"
    print(f"  ✓ wrote {html.relative_to(REPO)}")
    return 0 if html.is_file() else 1


def _warm_run_ingest(prefix: str) -> None:
    """Stage-1 fetch once per run prefix (shared cache for researcher tools)."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tools.baseline import default_config
    from tools.researchers.ingest import warm_ingest_cache

    print("\n== ingest: warm bundle (once per prefix) ==")
    bundle = warm_ingest_cache(default_config(), prefix)
    print(f"  ✓ prefix={bundle.prefix} preflight + crawl + structured")


def _stamp_run_prefix_on_tasks(prefix: str) -> None:
    """Annotate board tasks so workers know the run prefix for cache paths."""
    for row in _kanban_list_json():
        task_id = str(row.get("id") or "")
        if not task_id:
            continue
        _run_hermes("kanban", "comment", task_id, f"AI Digest run_prefix={prefix}")


def _init_run_telemetry(prefix: str) -> None:
    """Start pipeline + agent diagnostic collectors for a GO run."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from llm_pipeline.diagnostics import init_collector
    from tools.agent_diagnostics import init_agent_diagnostics
    from tools.baseline import agentic_config

    cfg = agentic_config()
    init_collector(prefix, cfg)
    init_agent_diagnostics(prefix, cfg)


def _finish_run_telemetry() -> None:
    """Write agent diagnostics (merges in-process LLM/tool records)."""
    from llm_pipeline import diagnostics as diag_mod
    from tools.agent_diagnostics import finish_agent_diagnostics, get_agent_diagnostics
    from tools.baseline import agentic_config

    if get_agent_diagnostics() is None:
        return
    finish_agent_diagnostics(agentic_config())
    diag_mod._active = None  # agent report already merged pipeline LLM calls


def cmd_diagnostics(args: argparse.Namespace) -> int:
    """Build or rebuild agent diagnostics waterfall for a run prefix."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from tools.agent_diagnostics import rebuild_from_artifacts
    from tools.baseline import agentic_config

    prefix = args.prefix or _resolve_run_prefix(None)
    try:
        path = rebuild_from_artifacts(prefix, agentic_config())
    except FileNotFoundError as exc:
        print(f"ERROR {exc}")
        return 1
    print(f"\n✓ diagnostics: {path.relative_to(REPO)}")
    html = path.with_suffix(".html")
    if html.is_file():
        print(f"  open: file://{html.resolve()}")
    return 0


def cmd_go(args: argparse.Namespace) -> int:
    """Concierge GO — kanban workers: research → librarian → synthesizer → render."""
    global _agentic_run_prefix

    if not _hermes_bin():
        print("hermes not on PATH.")
        return 1

    run_prefix = _resolve_run_prefix(args.prefix)
    _agentic_run_prefix = run_prefix
    _init_run_telemetry(run_prefix)

    print("== GO: Concierge pipeline ==")
    print("  Graph: research × N → librarian → synthesizer → render")
    print(f"  prefix: {run_prefix}")
    print("  mode: agent workers (plan → tools → artifacts)")

    from tools.agent_diagnostics import get_agent_diagnostics

    diag = get_agent_diagnostics()

    if args.fresh:
        print("\n-- fresh: archive existing digest tasks")
        if diag:
            with diag.phase("go.setup", "Concierge · board setup"):
                _archive_digest_board()
                if cmd_demo_board(argparse.Namespace(dry_run=False)) != 0:
                    _finish_run_telemetry()
                    return 1
        else:
            _archive_digest_board()
            if cmd_demo_board(argparse.Namespace(dry_run=False)) != 0:
                return 1
    else:
        existing = _research_rows()
        if not existing:
            if diag:
                with diag.phase("go.setup", "Concierge · demo board"):
                    if cmd_demo_board(argparse.Namespace(dry_run=False)) != 0:
                        _finish_run_telemetry()
                        return 1
            elif cmd_demo_board(argparse.Namespace(dry_run=False)) != 0:
                _finish_run_telemetry()
                return 1
        else:
            print(f"\n  reusing {len(existing)} research task(s) on board")

    rounds = max(1, int(args.rounds))
    if not args.skip_dispatch:
        _stamp_run_prefix_on_tasks(run_prefix)
        research_cm = diag.phase("go.research", "Research workers") if diag else None
        if research_cm:
            research_cm.__enter__()
        try:
            for round_num in range(1, rounds + 1):
                print(f"\n== GO round {round_num}/{rounds}: dispatch research ==")
                dispatch_args = argparse.Namespace(redo_invalid=True)
                cmd_dispatch_research(dispatch_args)
                research = _research_rows()
                ok = sum(1 for r in research if _research_artifact_ok(r))
                print(f"  artifact gate: {ok}/{len(research)}")
                if ok == len(research):
                    break
        finally:
            if research_cm:
                research_cm.__exit__(None, None, None)
        research = _research_rows()
        ok = sum(1 for r in research if _research_artifact_ok(r))
        if ok < len(research):
            print(f"\n✗ Phase A incomplete: {ok}/{len(research)} research tasks passed artifact gate")
            _finish_run_telemetry()
            return 1
        print(f"\n✓ Phase A: {ok}/{len(research)} research tasks with valid output.md")
        _persist_research_artifacts(run_prefix)
        lib_cm = diag.phase("go.librarian", "Librarian · merge & classify") if diag else None
        if lib_cm:
            lib_cm.__enter__()
        try:
            lib_rc = _dispatch_role_task(
                "Librarian: merge & classify",
                validate=validate_librarian_artifact,
                artifact_name=LIBRARIAN_ARTIFACT,
                prefix=run_prefix,
            )
        finally:
            if lib_cm:
                lib_cm.__exit__(None, None, None)
        if lib_rc != 0:
            print("\n✗ Phase B incomplete: librarian artifact gate failed")
            _finish_run_telemetry()
            return 1
        print("\n✓ Phase B (librarian): librarian.md passed artifact gate")
        syn_cm = diag.phase("go.synthesizer", "Synthesizer · digest JSON") if diag else None
        if syn_cm:
            syn_cm.__enter__()
        try:
            syn_rc = _dispatch_role_task(
                "Synthesize digest",
                validate=validate_synthesizer_artifact,
                artifact_name=DIGEST_ARTIFACT,
                prefix=run_prefix,
            )
        finally:
            if syn_cm:
                syn_cm.__exit__(None, None, None)
        if syn_rc != 0:
            print("\n✗ Phase B incomplete: synthesizer digest.json gate failed")
            _finish_run_telemetry()
            return 1
        print("\n✓ Phase B (synthesizer): digest.json passed artifact gate")
    else:
        print("\n-- skip-dispatch: using existing board artifacts")

    handover_only = bool(getattr(args, "handover_only", False))
    if handover_only:
        tasks = _handover_board_snapshot()
        ok_chain, issues = _handover_chain_ok()
        if not ok_chain:
            for issue in issues:
                print(f"  ✗ {issue}")
            return 1
        print("\n== verify: all digest tasks done ==")
        for t in tasks:
            print(f"  ✓ {t['id']} {t['title']} ({t['status']})")
        if _hermes_bin():
            _cleanup_board_after_go()
        board_clear = len(_digest_board_rows()) == 0
        receipt, trace = _write_handover_receipt(
            run_prefix, tasks=tasks, board_clear=board_clear
        )
        print(f"\n✓ Receipt: {receipt.relative_to(REPO)}")
        from tools.handover_trace import format_trace_summary

        print("\n== provenance trace ==")
        for line in format_trace_summary(trace):
            print(line)
        if board_clear:
            print("✓ Board clear (0 open digest tasks)")
        else:
            print("✗ Board not clear after cleanup")
            return 1
        print("\n✓ verify-handover PASSED (no report render)")
        return 0

    render_args = argparse.Namespace(prefix=run_prefix)
    if diag:
        with diag.phase("go.render", "Render · validate & HTML"):
            render_rc = cmd_render_from_board(render_args)
    else:
        render_rc = cmd_render_from_board(render_args)
    if render_rc != 0:
        print("\n✗ Phase C failed: render-from-board")
        _finish_run_telemetry()
        return 1
    report = _agentic_reports_dir() / f"{run_prefix}.html"
    print(f"\n✓ Report: {report.relative_to(REPO)}")
    if _hermes_bin():
        tasks = _handover_board_snapshot()
        _, trace = _write_handover_receipt(
            run_prefix,
            tasks=tasks,
            board_clear=True,
        )
        from tools.handover_trace import format_trace_summary

        print(f"  trace: agentic/hermes/.runtime/artifacts/{run_prefix}/handover.json")
        for line in format_trace_summary(trace):
            print(line)
    if _hermes_bin():
        _cleanup_board_after_go()
    _finish_run_telemetry()
    print("\n✓ GO completed (research → librarian → synthesizer → render)")
    return 0


def cmd_verify_handover(_: argparse.Namespace) -> int:
    """Smoke-test full worker pipeline; receipt at .runtime/artifacts/<prefix>/handover.json."""
    return cmd_go(
        argparse.Namespace(
            fresh=True,
            rounds=1,
            prefix=None,
            skip_dispatch=False,
            handover_only=True,
        )
    )


def cmd_generate_report(_: argparse.Namespace) -> int:
    """Generate a digest report — same as `go --fresh --rounds 1`."""
    return cmd_go(
        argparse.Namespace(
            fresh=True,
            rounds=1,
            prefix=None,
            skip_dispatch=False,
        )
    )


def _kanban_show_json(task_id: str) -> dict[str, Any]:
    proc = _run_hermes("kanban", "show", task_id, "--json")
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        sys.exit(proc.returncode)
    return json.loads(proc.stdout)


def _kanban_list_json() -> list[dict[str, Any]]:
    proc = _run_hermes("kanban", "list", "--json")
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        sys.exit(proc.returncode)
    return json.loads(proc.stdout)


def _research_topic(title: str) -> str:
    if title.lower().startswith("research:"):
        return title.split(":", 1)[1].strip()
    return title.strip()


def _task_workspace(task: dict[str, Any]) -> Path:
    path = task.get("workspace_path")
    if path:
        return Path(path)
    return HERMES_HOME / "kanban" / "workspaces" / task["id"]


def _researcher_workspace(task: dict[str, Any]) -> Path:
    return _task_workspace(task)


def _find_librarian_id() -> str | None:
    for row in _kanban_list_json():
        if row.get("title") == "Librarian: merge & classify":
            return row["id"]
    return None


def _demo_goal_settings() -> tuple[bool, int | None]:
    goal_cfg = _load_roles().get("demo_goal") or {}
    goal = bool(goal_cfg.get("enabled", True))
    max_turns = goal_cfg.get("max_turns")
    return goal, int(max_turns) if max_turns is not None else None


def _replace_research_task(task_id: str, librarian_id: str) -> str:
    """Archive an invalid research task and recreate it linked to the librarian."""
    data = _kanban_show_json(task_id)
    topic = _research_topic(data["task"]["title"])
    goal, goal_max_turns = _demo_goal_settings()
    print(f"  ↻ replace {task_id} ({topic})")
    _run_hermes("kanban", "unlink", task_id, librarian_id)
    _run_hermes("kanban", "archive", task_id)
    _run_hermes("kanban", "archive", "--rm", task_id)
    new_id = _kanban_create_json(
        f"Research: {topic}",
        assignee=RESEARCHER,
        body=_research_body(topic, prefix=_agentic_run_prefix),
        goal=goal,
        goal_max_turns=goal_max_turns,
    )
    _run_hermes("kanban", "link", new_id, librarian_id)
    return new_id


def _librarian_workspace() -> Path | None:
    row = _find_task_by_title("Librarian: merge & classify")
    if not row:
        return None
    return _task_workspace(_kanban_show_json(row["id"])["task"])


def _prepare_task(task_id: str) -> bool:
    """Promote/unblock; stage librarian.md before synthesizer dispatch."""
    _ensure_task_ready(task_id)
    task = _kanban_show_json(task_id)["task"]
    title = str(task.get("title") or "")
    prefix = _prepare_prefix or _agentic_run_prefix
    if title == "Synthesize digest" and prefix:
        ws = _task_workspace(task)
        staged = stage_librarian_for_workspace(
            prefix, ws, librarian_workspace=_librarian_workspace()
        )
        if staged:
            print(f"  staged: {LIBRARIAN_ARTIFACT} → {ws}")
    return True


def _materialize_role_artifact(
    task_id: str,
    title: str,
    *,
    prefix: str | None = None,
) -> None:
    """Persist worker artifacts to .runtime after kanban_complete."""
    task = _kanban_show_json(task_id)["task"]
    ws = _task_workspace(task)
    run_prefix = prefix or _agentic_run_prefix or _resolve_run_prefix(None)
    if title == "Librarian: merge & classify":
        cached = persist_librarian(run_prefix, ws)
        if cached:
            print(f"  cache: {LIBRARIAN_ARTIFACT} → {cached.relative_to(HERMES_PKG)}")
    elif title == "Synthesize digest":
        cached = persist_digest(run_prefix, ws)
        if cached:
            print(f"  cache: {DIGEST_ARTIFACT} → {cached.relative_to(HERMES_PKG)}")
        write_manifest(
            run_prefix,
            {
                "task_id": task_id,
                "title": title,
                "prefix": run_prefix,
            },
        )


_prepare_prefix: str | None = None
_agentic_run_prefix: str | None = None


def _resolve_run_prefix(explicit: str | None) -> str:
    if explicit:
        return explicit
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _persist_research_artifacts(prefix: str) -> None:
    for row in _research_rows():
        topic = _research_topic(str(row.get("title", "")))
        ws = _researcher_workspace(row)
        if validate_researcher_artifact(ws):
            continue
        path = persist_research(prefix, topic, ws)
        if path:
            print(f"  cache: research/{topic}.md → {path.name}")


def _role_artifact_locations(
    task: dict[str, Any],
    title: str,
    *,
    prefix: str | None,
) -> list[Path]:
    """Workspace first, then persisted runtime dir (survives Hermes workspace wipe)."""
    locs: list[Path] = [_task_workspace(task)]
    run_prefix = prefix or _agentic_run_prefix
    if run_prefix and title in {"Librarian: merge & classify", "Synthesize digest"}:
        locs.append(run_dir(run_prefix))
    seen: set[str] = set()
    out: list[Path] = []
    for path in locs:
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def _validate_role_artifact(
    task: dict[str, Any],
    title: str,
    validate: Any,
    *,
    prefix: str | None,
) -> tuple[list[str], Path | None]:
    """Return validation errors and the first location that passed (if any)."""
    for loc in _role_artifact_locations(task, title, prefix=prefix):
        errors = validate(loc)
        if not errors:
            return [], loc
    return validate(_task_workspace(task)), None


def _replace_synthesizer_task(task_id: str, librarian_id: str) -> str:
    """Archive an invalid synthesizer task and recreate it linked to the librarian."""
    goal, goal_max_turns = _demo_goal_settings()
    print(f"  ↻ replace {task_id} (synthesizer)")
    _run_hermes("kanban", "unlink", task_id, librarian_id)
    _run_hermes("kanban", "archive", task_id)
    _run_hermes("kanban", "archive", "--rm", task_id)
    new_id = _kanban_create_json(
        "Synthesize digest",
        assignee=SYNTHESIZER,
        body=_synthesizer_body(prefix=_agentic_run_prefix),
        parents=[librarian_id],
        goal=goal,
        goal_max_turns=goal_max_turns,
    )
    return new_id


def _dispatch_role_task(
    title: str,
    *,
    validate: Any,
    artifact_name: str,
    prefix: str | None = None,
) -> int:
    """Dispatch one downstream role task and enforce its artifact gate."""
    global _prepare_prefix
    row = _find_task_by_title(title)
    if not row:
        print(f"ERROR missing task {title!r}")
        return 1
    task_id = row["id"]
    print(f"\n▶ {task_id} ({title})")

    if row.get("status") == "done":
        _materialize_role_artifact(task_id, title, prefix=prefix)
        task = _kanban_show_json(task_id)["task"]
        errors, _ok_loc = _validate_role_artifact(task, title, validate, prefix=prefix)
        if not errors:
            print(f"  ✓ already done with valid {artifact_name}")
            return 0
        if title == "Synthesize digest":
            lib_row = _find_task_by_title("Librarian: merge & classify")
            if lib_row and lib_row.get("status") == "done":
                task_id = _replace_synthesizer_task(task_id, lib_row["id"])
                print(f"    recreated → {task_id}")
            else:
                print(f"  ✗ artifact gate: {', '.join(errors)}")
                return 1
        else:
            print(f"  ✗ artifact gate: {', '.join(errors)}")
            return 1

    row = _kanban_show_json(task_id)["task"]
    if row.get("status") == "blocked":
        _run_hermes("kanban", "unblock", task_id)
    _prepare_prefix = prefix
    status = _dispatch_one(task_id, title=title, prefix=prefix)
    _prepare_prefix = None
    print(f"  worker finished: {status}")
    if status != "done":
        print(f"  ✗ not done ({status})")
        return 1
    _materialize_role_artifact(task_id, title, prefix=prefix)
    task = _kanban_show_json(task_id)["task"]
    errors, ok_loc = _validate_role_artifact(task, title, validate, prefix=prefix)
    if errors:
        print(f"  ✗ artifact gate: {', '.join(errors)}")
        return 1
    print(f"  ✓ artifact ok: {ok_loc / artifact_name if ok_loc else artifact_name}")
    return 0


def _dispatch_one(
    task_id: str,
    *,
    title: str | None = None,
    prefix: str | None = None,
    timeout_s: int = 900,
    interval_s: int = 3,
) -> str:
    from datetime import datetime, timezone

    from tools.agent_diagnostics import get_agent_diagnostics

    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    t0 = time.perf_counter()
    task0 = _kanban_show_json(task_id)["task"]
    profile = str(task0.get("assignee") or "unknown")
    task_title = title or str(task0.get("title") or task_id)
    deadline = time.time() + timeout_s
    prepared = False
    prev_status: str | None = None

    def _finish(status: str) -> str:
        ended_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        duration_ms = (time.perf_counter() - t0) * 1000
        col = get_agent_diagnostics()
        if col:
            col.record_task(
                task_id=task_id,
                title=task_title,
                profile=profile,
                started_at=started_at,
                ended_at=ended_at,
                duration_ms=duration_ms,
                ok=status == "done",
                status=status,
            )
        return status

    while time.time() < deadline:
        task = _kanban_show_json(task_id)["task"]
        status = task["status"]
        if status == "done" and prev_status != "done" and title:
            # Hermes may wipe scratch workspaces on kanban_complete — snapshot immediately.
            _materialize_role_artifact(task_id, title, prefix=prefix)
        prev_status = status
        if status in {"done", "blocked", "failed", "archived"}:
            return _finish(status)
        if status in {"ready", "todo"}:
            if not prepared:
                if not _prepare_task(task_id):
                    return _finish("failed")
                prepared = True
            proc = _run_hermes("kanban", "dispatch", "--max", "1")
            if proc.returncode != 0:
                print(proc.stderr or proc.stdout)
                sys.exit(proc.returncode)
        time.sleep(interval_s)
    return _finish("timeout")


def _ensure_task_ready(task_id: str) -> None:
    status = _kanban_show_json(task_id)["task"]["status"]
    if status == "blocked":
        _run_hermes("kanban", "unblock", task_id)
    elif status == "todo":
        _run_hermes("kanban", "promote", task_id)


def _research_artifact_ok(row: dict[str, Any]) -> bool:
    return not validate_researcher_artifact(_researcher_workspace(row))


def cmd_dispatch_research(args: argparse.Namespace) -> int:
    """Dispatch researcher tasks with post-run output.md artifact gate."""
    if not _hermes_bin():
        print("hermes not on PATH.")
        return 1

    librarian_id = _find_librarian_id()
    if not librarian_id:
        print("ERROR no librarian task on board — run demo-board first")
        return 1

    rows = _kanban_list_json()
    research = [r for r in rows if str(r.get("title", "")).startswith("Research:")]

    if args.redo_invalid:
        print("== dispatch-research: redo invalid ==")
        for row in list(research):
            ws = _researcher_workspace(row)
            if validate_researcher_artifact(ws):
                new_id = _replace_research_task(row["id"], librarian_id)
                print(f"    recreated → {new_id}")
        research = [
            r for r in _kanban_list_json() if str(r.get("title", "")).startswith("Research:")
        ]

    ok = sum(1 for r in research if _research_artifact_ok(r))

    pending = [
        r for r in research
        if r["status"] in {"ready", "blocked", "todo"}
    ]
    if not pending:
        if ok == len(research):
            print(f"All {len(research)} research tasks passed artifact gate.")
            return 0
        print("No research tasks to dispatch (check in_progress or invalid done).")
    else:
        print(f"== dispatch-research: {len(pending)} task(s) ==")

    for row in pending:
        task_id = row["id"]
        topic = _research_topic(row["title"])
        print(f"\n▶ {task_id} ({topic})")
        if row["status"] == "blocked":
            _run_hermes("kanban", "unblock", task_id)
        status = _dispatch_one(task_id)
        print(f"  worker finished: {status}")
        task = _kanban_show_json(task_id)["task"]
        ws = _researcher_workspace(task)
        errors = validate_researcher_artifact(ws)
        if status != "done":
            print(f"  ✗ not done ({status})")
            continue
        if errors:
            print(f"  ✗ artifact gate: {', '.join(errors)}")
            if args.redo_invalid:
                new_id = _replace_research_task(task_id, librarian_id)
                print(f"  ↻ retrying {new_id}")
                status = _dispatch_one(new_id)
                print(f"  worker finished: {status}")
                if status == "done":
                    task = _kanban_show_json(new_id)["task"]
                    ws = _researcher_workspace(task)
                    errors = validate_researcher_artifact(ws)
            if errors:
                continue
            print(f"  ✓ artifact ok: {ws / 'output.md'}")
        else:
            print(f"  ✓ artifact ok: {ws / 'output.md'}")
        if _agentic_run_prefix:
            topic = _research_topic(str(task.get("title", "")))
            cached = persist_research(_agentic_run_prefix, topic, ws)
            if cached:
                print(f"  cache: research/{topic}.md")
        ok += 1

    print(f"\n== dispatch-research: {ok}/{len(research)} passed artifact gate ==")
    return 0 if ok == len(research) else 1


def cmd_demo_board(args: argparse.Namespace) -> int:
    if not _hermes_bin():
        print("hermes not on PATH.")
        return 1

    spec = _load_roles()
    topics = spec.get("demo_topics") or ["aisearch", "robotics", "llm", "rag"]
    dry_run = args.dry_run
    goal_cfg = spec.get("demo_goal") or {}
    goal = bool(goal_cfg.get("enabled", True))
    goal_max_turns = goal_cfg.get("max_turns")
    if goal_max_turns is not None:
        goal_max_turns = int(goal_max_turns)

    print("== demo-board: AI Digest Phase 2 POC ==")
    print("  Graph: research × N → librarian → synthesizer")
    print(f"  Topics ({len(topics)}): {', '.join(topics)}")
    if goal:
        turns_note = f", max_turns={goal_max_turns}" if goal_max_turns else ""
        print(f"  Goal mode: on{turns_note} (Ralph loop until kanban_complete)")

    research_ids: list[str] = []
    for topic in topics:
        title = f"Research: {topic}"
        if not dry_run:
            print(f"\n  + {title}")
        research_ids.append(
            _kanban_create_json(
                title,
                assignee=RESEARCHER,
                body=_research_body(topic, prefix=_agentic_run_prefix),
                goal=goal,
                goal_max_turns=goal_max_turns,
                dry_run=dry_run,
            )
        )

    if not dry_run:
        print("\n  + Librarian: merge & classify")
    librarian_id = _kanban_create_json(
        "Librarian: merge & classify",
        assignee=LIBRARIAN,
        body=_librarian_body(prefix=_agentic_run_prefix),
        parents=research_ids,
        goal=goal,
        goal_max_turns=goal_max_turns,
        dry_run=dry_run,
    )

    if not dry_run:
        print("\n  + Synthesize digest")
    synthesizer_id = _kanban_create_json(
        "Synthesize digest",
        assignee=SYNTHESIZER,
        body=_synthesizer_body(prefix=_agentic_run_prefix),
        parents=[librarian_id],
        goal=goal,
        goal_max_turns=goal_max_turns,
        dry_run=dry_run,
    )

    print("\n== demo-board: done ==")
    if dry_run:
        print("  Re-run without --dry-run to create tasks.")
    else:
        print(f"  librarian={librarian_id}  synthesizer={synthesizer_id}")
        print("  hermes config set kanban.max_in_progress 1   # laptop")
        print("  hermes gateway start                          # if not running")
        print("  hermes kanban dispatch --max 1                # repeat until drained")
        print("  hermes kanban list")
    return 0


def _ensure_runtime_dirs() -> None:
    for sub in ("board", "memory", "logs", "artifacts"):
        (RUNTIME / sub).mkdir(parents=True, exist_ok=True)


def cmd_bootstrap(args: argparse.Namespace) -> int:
    print("== agentic bootstrap ==")
    _ensure_runtime_dirs()
    if args.skip_setup:
        print("Skipping Hermes profile setup (--skip-setup).")
        return 0
    return setup_agents(quiet=False)


def cmd_setup(args: argparse.Namespace) -> int:
    return setup_agents(dry_run=args.dry_run)


def cmd_board_status(_: argparse.Namespace) -> int:
    """Deterministic kanban + artifact gate snapshot (Concierge STATUS)."""
    from tools.orchestration import board_status

    print(json.dumps(board_status(), indent=2))
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    print(f"Repo: {REPO}")
    print(f"Hermes pkg: {HERMES_PKG.relative_to(REPO)}")
    rows = [
        (".runtime", RUNTIME.is_dir()),
        ("config/hermes_roles.yaml", ROLES_PATH.is_file()),
    ]
    for name, ok in rows:
        print(f"  {'✓' if ok else '·'} {name}")
    hermes = _hermes_bin()
    print(f"  {'✓' if hermes else '·'} hermes CLI ({hermes or 'not on PATH'})")
    return 0


def _rm(path: Path) -> None:
    if not path.exists():
        return
    print(f"  rm {path.relative_to(REPO)}")
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def cmd_nuke(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Dry run — re-run with --yes to clear agentic/hermes/.runtime")
        sys.exit(1)
    print("== nuke agentic ephemeral ==")
    manifest = _load_manifest()
    for rel in manifest.get("ephemeral", {}).get("dirs", []):
        _rm(REPO / rel)
    _ensure_runtime_dirs()
    print("Agentic runtime cleared.")
    return 0


def cmd_hermes(args: argparse.Namespace) -> int:
    argv = list(args.hermes_args or ["profile", "list"])
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        argv = ["profile", "list"]
    hermes = _hermes_bin()
    if not hermes:
        print("hermes not on PATH.")
        return 1
    print(f"$ hermes {' '.join(argv)}")
    return subprocess.run([hermes, *argv], cwd=REPO).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Agentic Hermes admin")
    sub = parser.add_subparsers(dest="command", required=True)

    p_boot = sub.add_parser("bootstrap", help="ensure .runtime + optional setup")
    p_boot.add_argument("--skip-setup", action="store_true", help="only create .runtime dirs")
    p_boot.set_defaults(func=cmd_bootstrap)

    p_setup = sub.add_parser("setup", help="Ollama + digest role profiles + kanban")
    p_setup.add_argument("--dry-run", action="store_true")
    p_setup.set_defaults(func=cmd_setup)

    p_board = sub.add_parser(
        "demo-board",
        help="create Phase 2 POC kanban graph (research × N → librarian → synthesizer)",
    )
    p_board.add_argument("--dry-run", action="store_true")
    p_board.set_defaults(func=cmd_demo_board)

    p_dispatch = sub.add_parser(
        "dispatch-research",
        help="dispatch researcher tasks; enforce output.md artifact gate",
    )
    p_dispatch.add_argument(
        "--redo-invalid",
        action="store_true",
        help="archive/recreate done tasks that fail the artifact gate",
    )
    p_dispatch.set_defaults(func=cmd_dispatch_research)

    p_render = sub.add_parser(
        "render-from-board",
        help="assemble digest from researcher artifacts and render HTML (Phase B)",
    )
    p_render.add_argument("--prefix", default=None, help="run prefix YYYYMMDDHHMMSS")
    p_render.set_defaults(func=cmd_render_from_board)

    p_go = sub.add_parser(
        "go",
        help="Concierge GO: create board, dispatch research, render report (Phases A→C)",
    )
    p_go.add_argument("--fresh", action="store_true", help="archive existing digest tasks first")
    p_go.add_argument("--rounds", type=int, default=2, help="max dispatch-research rounds")
    p_go.add_argument("--prefix", default=None, help="run prefix for rendered report")
    p_go.add_argument(
        "--skip-dispatch",
        action="store_true",
        help="skip worker dispatch (render from existing artifacts only)",
    )
    p_go.set_defaults(func=cmd_go)

    p_diag = sub.add_parser(
        "diagnostics",
        help="build agent diagnostics waterfall for a run prefix (from handover + artifacts)",
    )
    p_diag.add_argument("--prefix", default=None, help="run prefix YYYYMMDDHHMMSS")
    p_diag.set_defaults(func=cmd_diagnostics)

    p_gen = sub.add_parser(
        "generate-report",
        help="generate digest HTML+JSON (go --fresh --rounds 1)",
    )
    p_gen.set_defaults(func=cmd_generate_report)

    p_verify = sub.add_parser(
        "verify-handover",
        help="smoke-test kanban handover; receipt at .runtime/artifacts/<prefix>/handover.json",
    )
    p_verify.set_defaults(func=cmd_verify_handover)

    p_nuke = sub.add_parser("nuke", help="clear agentic/hermes/.runtime")
    p_nuke.add_argument("--yes", action="store_true")
    p_nuke.set_defaults(func=cmd_nuke)

    p_st = sub.add_parser("status", help="agentic paths and hermes CLI")
    p_st.set_defaults(func=cmd_status)

    p_bs = sub.add_parser(
        "board-status",
        help="kanban pipeline snapshot + artifact gates (Concierge STATUS)",
    )
    p_bs.set_defaults(func=cmd_board_status)

    p_h = sub.add_parser("hermes", help="passthrough to upstream hermes CLI")
    p_h.add_argument("hermes_args", nargs=argparse.REMAINDER)
    p_h.set_defaults(func=cmd_hermes)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
