"""Tests for agentic/hermes/admin/manage.py — gateway health check + auto-fallback."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Load manage.py directly by path to avoid import resolution conflicts
_MANAGE_PATH = REPO / "agentic" / "hermes" / "admin" / "manage.py"
_spec = importlib.util.spec_from_file_location("hermes_manage", _MANAGE_PATH)
assert _spec and _spec.loader
hermes_manage = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hermes_manage)

_hermes_gateway_health = hermes_manage._hermes_gateway_health


class TestHermesGatewayHealth:
    """Verify _hermes_gateway_health() returns correct (healthy, message) tuples."""

    def test_herms_not_on_path(self):
        """When hermes binary is missing, returns unhealthy with clear message."""
        with patch("hermes_manage._hermes_bin", return_value=None):
            healthy, msg = _hermes_gateway_health()
        assert healthy is False
        assert "not found on PATH" in msg

    def test_herms_binary_not_found(self):
        """When hermes binary path exists but file not found, returns unhealthy."""
        with patch("hermes_manage._hermes_bin", return_value="/nonexistent/hermes"):
            with patch("subprocess.run", side_effect=FileNotFoundError()):
                healthy, msg = _hermes_gateway_health()
        assert healthy is False
        assert "not found on PATH" in msg

    def test_gateway_unreachable(self):
        """When gateway returns connection error, returns unhealthy."""
        proc = MagicMock()
        proc.returncode = 1
        proc.stderr = "Error: gateway connection refused"
        proc.stdout = ""
        with patch("hermes_manage._hermes_bin", return_value="/usr/local/bin/hermes"):
            with patch("subprocess.run", return_value=proc):
                healthy, msg = _hermes_gateway_health()
        assert healthy is False
        assert "Gateway unreachable" in msg

    def test_kanban_list_failed(self):
        """When kanban list fails without gateway keyword, returns unhealthy."""
        proc = MagicMock()
        proc.returncode = 2
        proc.stderr = ""
        proc.stdout = "invalid command"
        with patch("hermes_manage._hermes_bin", return_value="/usr/local/bin/hermes"):
            with patch("subprocess.run", return_value=proc):
                healthy, msg = _hermes_gateway_health()
        assert healthy is False
        assert "Kanban list failed" in msg

    def test_non_json_response(self):
        """When gateway returns non-JSON stdout, returns unhealthy."""
        proc = MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        proc.stdout = "not a json response"
        with patch("hermes_manage._hermes_bin", return_value="/usr/local/bin/hermes"):
            with patch("subprocess.run", return_value=proc):
                healthy, msg = _hermes_gateway_health()
        assert healthy is False
        assert "non-JSON" in msg

    def test_timeout(self):
        """When health check times out, returns unhealthy."""
        with patch("hermes_manage._hermes_bin", return_value="/usr/local/bin/hermes"):
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["hermes"], timeout=10)):
                healthy, msg = _hermes_gateway_health()
        assert healthy is False
        assert "timed out" in msg

    def test_healthy_valid_json(self):
        """When gateway returns valid JSON, returns healthy."""
        proc = MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        proc.stdout = json.dumps([{"id": "task-1", "title": "Research: AI"}])
        with patch("hermes_manage._hermes_bin", return_value="/usr/local/bin/hermes"):
            with patch("subprocess.run", return_value=proc):
                healthy, msg = _hermes_gateway_health()
        assert healthy is True
        assert msg == ""

    def test_healthy_empty_json_array(self):
        """When gateway returns empty JSON array, returns healthy (no tasks but gateway up)."""
        proc = MagicMock()
        proc.returncode = 0
        proc.stderr = ""
        proc.stdout = "[]"
        with patch("hermes_manage._hermes_bin", return_value="/usr/local/bin/hermes"):
            with patch("subprocess.run", return_value=proc):
                healthy, msg = _hermes_gateway_health()
        assert healthy is True
        assert msg == ""
