"""AI Digest Hermes plugin — generic ingest tools for researcher workers."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import schemas

_HERMES_PKG = Path(__file__).resolve().parents[2]
_REPO_ROOT = _HERMES_PKG.parent.parent
for _p in (_REPO_ROOT, _HERMES_PKG):
    _ps = str(_p)
    if _ps not in sys.path:
        sys.path.insert(0, _ps)

from lib.ingest.web import verify_url  # noqa: E402


def register(ctx) -> None:
    ctx.register_tool(
        name="verify_url",
        toolset="digest",
        schema=schemas.VERIFY_URL,
        handler=verify_url_json,
    )
    ctx.register_tool(
        name="fetch_rss",
        toolset="digest",
        schema=schemas.FETCH_RSS,
        handler=fetch_rss_json,
    )
    ctx.register_tool(
        name="read_preflight_category",
        toolset="digest",
        schema=schemas.READ_PREFLIGHT_CATEGORY,
        handler=read_preflight_category_json,
    )
    ctx.register_tool(
        name="read_crawl_markdown",
        toolset="digest",
        schema=schemas.READ_CRAWL_MARKDOWN,
        handler=read_crawl_markdown_json,
    )
    ctx.register_tool(
        name="read_structured_json",
        toolset="digest",
        schema=schemas.READ_STRUCTURED_JSON,
        handler=read_structured_json_json,
    )
    ctx.register_tool(
        name="read_topic_config",
        toolset="digest",
        schema=schemas.READ_TOPIC_CONFIG,
        handler=read_topic_config_json,
    )
    ctx.register_tool(
        name="synthesize_digest",
        toolset="digest",
        schema=schemas.SYNTHESIZE_DIGEST,
        handler=synthesize_digest_json,
    )
    ctx.register_tool(
        name="digest_board_status",
        toolset="digest_admin",
        schema=schemas.DIGEST_BOARD_STATUS,
        handler=digest_board_status_json,
    )
    ctx.register_tool(
        name="digest_setup_board",
        toolset="digest_admin",
        schema=schemas.DIGEST_SETUP_BOARD,
        handler=digest_setup_board_json,
    )
    ctx.register_tool(
        name="digest_go",
        toolset="digest_admin",
        schema=schemas.DIGEST_GO,
        handler=digest_go_json,
    )
    ctx.register_tool(
        name="digest_assess_run",
        toolset="digest_admin",
        schema=schemas.DIGEST_ASSESS_RUN,
        handler=digest_assess_run_json,
    )
    ctx.register_tool(
        name="digest_deploy_app",
        toolset="digest_admin",
        schema=schemas.DIGEST_DEPLOY_APP,
        handler=digest_deploy_app_json,
    )
    ctx.register_tool(
        name="digest_publish",
        toolset="digest_admin",
        schema=schemas.DIGEST_PUBLISH,
        handler=digest_publish_json,
    )
    ctx.register_tool(
        name="digest_open_report",
        toolset="digest_admin",
        schema=schemas.DIGEST_OPEN_REPORT,
        handler=digest_open_report_json,
    )


def _repo_root() -> Path:
    return _REPO_ROOT


def _ensure_repo_path() -> None:
    repo = _repo_root()
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))


def _overlay_agentic_tool(stem: str):
    """Load ``agentic/hermes/tools/<stem>.py`` as ``tools.<stem>`` inside Hermes workers.

    Hermes CLI already imports its own top-level ``tools`` package; overlaying
    individual submodules lets digest handlers reach AI Digest adapters without
    clobbering built-in Hermes tools.
    """
    _ensure_repo_path()
    key = f"tools.{stem}"
    path = _HERMES_PKG / "tools" / f"{stem}.py"
    existing = sys.modules.get(key)
    if existing is not None and getattr(existing, "__file__", None) == str(path):
        return existing
    spec = importlib.util.spec_from_file_location(key, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load agentic tool module: {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    spec.loader.exec_module(mod)
    return mod


def _default_prefix(args: dict) -> str:
    return str(args.get("prefix") or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))


def verify_url_json(args: dict, **kwargs) -> str:
    try:
        timeout = int(args.get("timeout", 8))
    except (TypeError, ValueError):
        timeout = 8
    return json.dumps(verify_url(str(args.get("url") or ""), timeout=timeout), default=str)


def fetch_rss_json(args: dict, **kwargs) -> str:
    _ensure_repo_path()
    from lib.ingest.agent_tools import fetch_rss
    feeds = args.get("feeds")
    if feeds is not None and not isinstance(feeds, list):
        return json.dumps({"ok": False, "error": "feeds must be an array"})
    topic = str(args.get("topic") or "").strip() or None
    return json.dumps(fetch_rss(feeds, topic=topic), default=str)


def read_preflight_category_json(args: dict, **kwargs) -> str:
    _ensure_repo_path()
    from lib.ingest.agent_tools import read_preflight_category

    default_config = _overlay_agentic_tool("baseline").default_config
    prefix = _default_prefix(args)
    try:
        max_bullets = int(args.get("max_bullets", 12))
    except (TypeError, ValueError):
        max_bullets = 12
    topic = str(args.get("topic") or "").strip() or None
    result = read_preflight_category(
        default_config(),
        prefix,
        str(args.get("category_id") or ""),
        topic=topic,
        max_bullets=max_bullets,
    )
    return json.dumps(result, default=str)


def read_crawl_markdown_json(args: dict, **kwargs) -> str:
    _ensure_repo_path()
    from lib.ingest.agent_tools import read_crawl_markdown_tool

    default_config = _overlay_agentic_tool("baseline").default_config
    prefix = _default_prefix(args)
    try:
        max_chars = int(args.get("max_chars", 8000))
    except (TypeError, ValueError):
        max_chars = 8000
    topic = str(args.get("topic") or "").strip() or None
    result = read_crawl_markdown_tool(
        default_config(),
        prefix,
        str(args.get("slug") or ""),
        topic=topic,
        max_chars=max_chars,
    )
    return json.dumps(result, default=str)


def read_structured_json_json(args: dict, **kwargs) -> str:
    _ensure_repo_path()
    from lib.ingest.agent_tools import read_structured_json_tool

    default_config = _overlay_agentic_tool("baseline").default_config
    prefix = _default_prefix(args)
    topic = str(args.get("topic") or "").strip() or None
    result = read_structured_json_tool(
        default_config(),
        prefix,
        str(args.get("slug") or ""),
        topic=topic,
    )
    return json.dumps(result, default=str)


def read_topic_config_json(args: dict, **kwargs) -> str:
    _ensure_repo_path()
    from lib.ingest.agent_tools import read_topic_config

    return json.dumps(read_topic_config(str(args.get("topic") or "")), default=str)


def digest_board_status_json(args: dict, **kwargs) -> str:
    _overlay_agentic_tool("orchestration")
    from tools.orchestration import board_status

    brief = bool(args.get("brief", False))
    return json.dumps(board_status(brief=brief), default=str)


def digest_setup_board_json(args: dict, **kwargs) -> str:
    fresh = bool(args.get("fresh", False))
    start = str(args.get("start") or "").strip() or None
    history_raw = args.get("history")
    history: int | None = None
    if history_raw is not None and str(history_raw).strip() != "":
        try:
            history = int(history_raw)
        except (TypeError, ValueError):
            return json.dumps(
                {"ok": False, "error": f"invalid history: {history_raw!r}"},
            )
    prefix = str(args.get("prefix") or "").strip() or None
    venv_py = _REPO_ROOT / ".venv" / "bin" / "python"
    py = str(venv_py if venv_py.is_file() else Path(sys.executable))
    manage = _REPO_ROOT / "agentic" / "hermes" / "admin" / "manage.py"
    cmd = [py, str(manage), "demo-board"]
    if fresh:
        cmd.append("--fresh")
    if prefix:
        cmd.extend(["--prefix", prefix])
    if start:
        cmd.extend(["--start", start])
    if history is not None:
        cmd.extend(["--history", str(history)])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(_REPO_ROOT), timeout=120)
    except subprocess.TimeoutExpired:
        return json.dumps({"ok": False, "error": "digest_setup_board timed out"})
    payload: dict = {
        "ok": proc.returncode == 0,
        "fresh": fresh,
        "stdout": (proc.stdout or "")[-4000:],
        "stderr": (proc.stderr or "")[-2000:],
    }
    if proc.returncode == 0:
        from tools.orchestration import board_status
        from tools.topics import resolve_board_topics

        payload["board"] = board_status()
        payload["board_topics"] = resolve_board_topics()
    return json.dumps(payload, default=str)


def digest_go_json(args: dict, **kwargs) -> str:
    fresh = bool(args.get("fresh", False))
    prefix = str(args.get("prefix") or "").strip() or None
    start = str(args.get("start") or "").strip() or None
    history_raw = args.get("history")
    history: int | None = None
    if history_raw is not None and str(history_raw).strip() != "":
        try:
            history = int(history_raw)
        except (TypeError, ValueError):
            return json.dumps(
                {"ok": False, "error": f"invalid history: {history_raw!r}"},
            )
    pipeline = bool(args.get("pipeline", False))
    # Backward compat: old digest_go default was batch; explicit agents:false meant batch.
    legacy_agents = args.get("agents")
    if legacy_agents is False and not pipeline:
        pipeline = True
    try:
        rounds = int(args.get("rounds", 2))
    except (TypeError, ValueError):
        rounds = 2
    venv_py = _REPO_ROOT / ".venv" / "bin" / "python"
    py = str(venv_py if venv_py.is_file() else Path(sys.executable))
    manage = _REPO_ROOT / "agentic" / "hermes" / "admin" / "manage.py"
    cmd = [py, str(manage), "go"]
    if pipeline:
        cmd.append("--pipeline")
    else:
        cmd.append(f"--rounds={rounds}")
        if fresh:
            cmd.append("--fresh")
    if prefix:
        cmd.extend(["--prefix", prefix])
    if start:
        cmd.extend(["--start", start])
    if history is not None:
        cmd.extend(["--history", str(history)])
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=7200,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"ok": False, "error": "digest_go timed out after 7200s"})
    payload: dict = {
        "ok": proc.returncode == 0,
        "prefix": prefix,
        "stdout": (proc.stdout or "")[-6000:],
        "stderr": (proc.stderr or "")[-2000:],
    }
    from tools.orchestration import board_status

    payload["board"] = board_status()
    return json.dumps(payload, default=str)


def digest_assess_run_json(args: dict, **kwargs) -> str:
    publish = _overlay_agentic_tool("publish")
    prefix = str(args.get("prefix") or "").strip() or None
    compare = str(args.get("compare_prefix") or "").strip() or None
    force = bool(args.get("force", False))
    try:
        result = publish.assess_run(prefix, compare_prefix=compare, force=force)
    except (FileNotFoundError, ValueError) as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    return json.dumps(result, default=str)


def digest_deploy_app_json(args: dict, **kwargs) -> str:
    publish = _overlay_agentic_tool("publish")
    prefix = str(args.get("prefix") or "").strip() or None
    dry_run = bool(args.get("dry_run", False))
    force = bool(args.get("force", False))
    try:
        result = publish.deploy_to_app(prefix, dry_run=dry_run, force=force)
    except (FileNotFoundError, ValueError) as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    return json.dumps(result, default=str)


def digest_publish_json(args: dict, **kwargs) -> str:
    publish = _overlay_agentic_tool("publish")
    prefix = str(args.get("prefix") or "").strip() or None
    msg = str(args.get("commit_message") or "").strip() or None
    confirm_push = bool(args.get("confirm_push", False))
    dry_run = bool(args.get("dry_run", False))
    force = bool(args.get("force", False))
    try:
        result = publish.publish_run(
            prefix,
            commit_message=msg,
            confirm_push=confirm_push,
            dry_run=dry_run,
            force=force,
        )
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    return json.dumps(result, default=str)


def digest_open_report_json(args: dict, **kwargs) -> str:
    publish = _overlay_agentic_tool("publish")
    prefix = str(args.get("prefix") or "").strip() or None
    target = str(args.get("target") or "report").strip() or "report"
    dry_run = bool(args.get("dry_run", False))
    try:
        result = publish.open_report(prefix, target=target, dry_run=dry_run)
    except (FileNotFoundError, ValueError) as exc:
        return json.dumps({"ok": False, "error": str(exc)})
    return json.dumps(result, default=str)


def synthesize_digest_json(args: dict, **kwargs) -> str:
    workspace = Path(str(args.get("workspace") or ""))
    prefix = _default_prefix(args)
    if not workspace.is_dir():
        return json.dumps({"ok": False, "error": f"workspace not found: {workspace}"})

    venv_py = _REPO_ROOT / ".venv" / "bin" / "python"
    if not venv_py.is_file():
        return json.dumps(
            {
                "ok": False,
                "error": f"repo venv missing: {venv_py} — run python admin/manage.py bootstrap",
            }
        )
    py = str(venv_py)
    # Hermes workers shadow the upstream ``tools`` package — run synthesis in repo venv.
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(_HERMES_PKG)!r})\n"
        f"sys.path.insert(0, {str(_REPO_ROOT)!r})\n"
        "from pathlib import Path\n"
        "from tools.baseline import agentic_llm_config\n"
        "from tools.synthesize import synthesize_digest_from_librarian\n"
        "from tools.runtime_store import persist_digest\n"
        f"ws = Path({str(workspace)!r})\n"
        f"prefix = {prefix!r}\n"
        "result = synthesize_digest_from_librarian(ws, prefix=prefix, cfg=agentic_llm_config())\n"
        "if result.get('ok') and (ws / 'digest.json').is_file():\n"
        "    persist_digest(prefix, ws)\n"
        "print(json.dumps(result, default=str))\n"
    )
    try:
        proc = subprocess.run(
            [py, "-c", code],
            capture_output=True,
            text=True,
            cwd=str(_REPO_ROOT),
            timeout=900,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"ok": False, "error": "synthesize_digest timed out after 900s"})
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "unknown error").strip()
        return json.dumps({"ok": False, "error": err[-2000:]})
    out = proc.stdout.strip()
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return json.dumps({"ok": False, "error": f"invalid JSON from synthesizer: {out[:500]}"})
    return out
