"""Local dev server: digest archive, diagnostics, admin UI, and control API."""

from __future__ import annotations

import json
import mimetypes
import re
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from llm_pipeline.admin_ops import (
    PipelineMode,
    create_tuning_branch,
    delete_digest,
    get_job,
    git_commit,
    git_merge_main,
    git_push,
    git_status,
    list_digests,
    list_jobs,
    precheck_latest,
    read_config_bundle,
    run_precheck,
    start_pipeline,
    write_config_bundle,
)
from llm_pipeline.config import load_config
from lib.paths import LLM_PIPELINE_ROOT, REPO_ROOT

REPO = REPO_ROOT
DEFAULT_PORT = 8765
_active_server: ThreadingHTTPServer | None = None

# URL prefixes → directories (path traversal safe).
_STATIC_ROOTS: tuple[tuple[str, Path], ...] = (
    ("reports", LLM_PIPELINE_ROOT / "reports"),
    ("diagnostics", LLM_PIPELINE_ROOT / "diagnostics"),
    ("admin", LLM_PIPELINE_ROOT / "server"),
    ("server", LLM_PIPELINE_ROOT / "server"),
    ("assets", LLM_PIPELINE_ROOT / "assets"),
)


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: Any) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


def _redirect(handler: BaseHTTPRequestHandler, location: str) -> None:
    handler.send_response(302)
    handler.send_header("Location", location)
    handler.end_headers()


def _resolve_repo_file(url_path: str) -> Path | None:
    """Map a URL path to a file under the repo (or configured static roots)."""
    path = urllib.parse.unquote(url_path.split("?", 1)[0])
    if path in ("", "/"):
        return LLM_PIPELINE_ROOT / "reports" / "index.html"

    rel = path.lstrip("/")
    root = REPO.resolve()

    # Top-level files (config.yaml, index.html, …)
    direct = (root / rel).resolve()
    if str(direct).startswith(str(root)) and direct.is_file():
        return direct

    for prefix, base in _STATIC_ROOTS:
        if rel == prefix or rel.startswith(prefix + "/"):
            suffix = rel[len(prefix) :].lstrip("/")
            candidate = (base / suffix).resolve() if suffix else (base / "index.html").resolve()
            if str(candidate).startswith(str(base.resolve())):
                if candidate.is_dir():
                    index = candidate / "index.html"
                    return index if index.is_file() else None
                if candidate.is_file():
                    return candidate
    return None


def schedule_shutdown() -> None:
    """Stop serve_forever() from a request handler thread."""
    server = _active_server
    if server is None:
        return
    threading.Thread(target=server.shutdown, daemon=True).start()


class LocalSiteHandler(BaseHTTPRequestHandler):
    server_version = "AIDigestLocal/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path or "/"
        cfg = load_config()

        if path == "/api/health":
            return _json_response(
                self,
                200,
                {"ok": True, "service": "local", "readonly": False, "site": True},
            )
        if path == "/api/mode":
            return _json_response(
                self,
                200,
                {"deploy": "local", "readonly": False, "api": True, "site": True},
            )
        if path == "/api/git/status":
            return _json_response(self, 200, git_status())
        if path == "/api/config":
            bundle = read_config_bundle()
            bundle["git"] = git_status()
            return _json_response(self, 200, bundle)
        if path == "/api/digests":
            return _json_response(self, 200, {"digests": list_digests(cfg)})
        if path == "/api/jobs":
            return _json_response(self, 200, {"jobs": list_jobs()})
        if path.startswith("/api/jobs/"):
            job = get_job(path.split("/")[-1])
            if not job:
                return _json_response(self, 404, {"error": "job not found"})
            return _json_response(self, 200, job)
        if path == "/api/precheck":
            latest = precheck_latest()
            return _json_response(self, 200, latest or {"ok": False, "log": ["No precheck run yet."]})

        if path == "/":
            return _redirect(self, "/reports/index.html")

        target = _resolve_repo_file(path)
        if target is None:
            self.send_error(404)
            return
        return self._send_file(target)

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        body = _read_json(self)
        cfg = load_config()
        try:
            if path == "/api/precheck":
                return _json_response(self, 200, run_precheck())
            if path == "/api/git/branch":
                return _json_response(self, 200, create_tuning_branch(body.get("name")))
            if path == "/api/git/commit":
                return _json_response(self, 200, git_commit(body.get("message") or ""))
            if path == "/api/git/push":
                return _json_response(self, 200, git_push())
            if path == "/api/git/merge-main":
                return _json_response(self, 200, git_merge_main())
            if path == "/api/pipeline/run":
                mode = PipelineMode(body.get("mode") or "full")
                job = start_pipeline(
                    cfg,
                    mode=mode,
                    start=body.get("start"),
                    history=int(body.get("history") or 10),
                    prefix=body.get("prefix"),
                )
                return _json_response(self, 202, job.to_dict())
            if path == "/api/shutdown":
                _json_response(self, 200, {"ok": True, "message": "Server shutting down."})
                schedule_shutdown()
                return
        except (ValueError, PermissionError, RuntimeError) as exc:
            return _json_response(self, 400, {"error": str(exc)})
        return _json_response(self, 404, {"error": "not found"})

    def do_PUT(self) -> None:
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        body = _read_json(self)
        try:
            if path == "/api/config":
                result = write_config_bundle(
                    config_yaml=body.get("config_yaml"),
                    config_section=body.get("config_section"),
                    section_yaml=body.get("section_yaml"),
                    editorial_brief=body.get("editorial_brief"),
                    force_branch=bool(body.get("force_branch")),
                )
                return _json_response(self, 200, result)
        except (ValueError, PermissionError, RuntimeError) as exc:
            return _json_response(self, 400, {"error": str(exc)})
        return _json_response(self, 404, {"error": "not found"})

    def do_DELETE(self) -> None:
        path = urllib.parse.urlparse(self.path).path.rstrip("/")
        m = re.match(r"^/api/digests/(\d{14})$", path)
        if not m:
            return _json_response(self, 404, {"error": "not found"})
        try:
            result = delete_digest(load_config(), m.group(1))
            return _json_response(self, 200, result)
        except ValueError as exc:
            return _json_response(self, 400, {"error": str(exc)})

    def _send_file(self, target: Path) -> None:
        data = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def prepare_local_site(cfg: dict[str, Any] | None = None) -> None:
    """Ensure admin frame exists before serving."""
    from llm_pipeline.admin_frame import rebuild_admin_archive

    if cfg is None:
        cfg = load_config()
    rebuild_admin_archive(cfg)


def serve_local(
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    *,
    open_browser: bool = True,
    cfg: dict[str, Any] | None = None,
) -> None:
    """Serve reports, diagnostics, admin, and /api on localhost."""
    if cfg is None:
        cfg = load_config()
    prepare_local_site(cfg)
    url = f"http://{host}:{port}/"
    print(f"Local site:  {url}")
    print(f"  Archive:   {url}reports/index.html")
    print(f"  Diagnostics: {url}diagnostics/index.html")
    print(f"  Admin:     {url}admin/index.html")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(f"{url}reports/index.html")
    global _active_server
    server = ThreadingHTTPServer((host, port), LocalSiteHandler)
    _active_server = server
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
        _active_server = None


# Backward-compatible alias
serve = serve_local
