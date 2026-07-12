"""digest-tools plugin overlays agentic modules under Hermes' tools package."""

from __future__ import annotations

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path

from lib.paths import REPO_ROOT

ROOT = REPO_ROOT
HERMES_PKG = ROOT / "agentic" / "hermes"
PLUGIN_INIT = HERMES_PKG / "plugins" / "digest-tools" / "__init__.py"


def _load_digest_tools_plugin():
    """Load digest-tools __init__ with its sibling schemas module."""
    pkg_name = "digest_tools_plugin"
    pkg_dir = PLUGIN_INIT.parent
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    if str(HERMES_PKG) not in sys.path:
        sys.path.insert(0, str(HERMES_PKG))

    schemas_key = f"{pkg_name}.schemas"
    if schemas_key not in sys.modules:
        sch_spec = importlib.util.spec_from_file_location(
            schemas_key, pkg_dir / "schemas.py"
        )
        assert sch_spec and sch_spec.loader
        sch_mod = importlib.util.module_from_spec(sch_spec)
        sys.modules[schemas_key] = sch_mod
        sch_spec.loader.exec_module(sch_mod)

    init_spec = importlib.util.spec_from_file_location(pkg_name, PLUGIN_INIT)
    assert init_spec and init_spec.loader
    plugin = importlib.util.module_from_spec(init_spec)
    sys.modules[pkg_name] = plugin
    init_spec.loader.exec_module(plugin)
    return plugin


class DigestToolsOverlayTest(unittest.TestCase):
    def test_orchestration_loads_when_tools_package_shadowed(self) -> None:
        """Hermes ships its own ``tools`` package — overlay must preload profiles."""
        plugin = _load_digest_tools_plugin()

        fake_tools = types.ModuleType("tools")
        fake_tools.__path__ = []  # type: ignore[attr-defined]
        saved = {
            "tools": sys.modules.get("tools"),
            "tools.profiles": sys.modules.get("tools.profiles"),
            "tools.orchestration": sys.modules.get("tools.orchestration"),
            "tools.artifacts": sys.modules.get("tools.artifacts"),
            "tools.runtime_store": sys.modules.get("tools.runtime_store"),
        }
        sys.modules["tools"] = fake_tools
        for key in (
            "tools.profiles",
            "tools.orchestration",
            "tools.artifacts",
            "tools.runtime_store",
        ):
            sys.modules.pop(key, None)

        try:
            mod = plugin._overlay_agentic_tool("orchestration")
            self.assertTrue(hasattr(mod, "board_status"))
            profiles = sys.modules.get("tools.profiles")
            self.assertIsNotNone(profiles)
            self.assertEqual(
                str(getattr(profiles, "__file__", "")),
                str(HERMES_PKG / "tools/profiles.py"),
            )
            runtime_store = sys.modules.get("tools.runtime_store")
            self.assertIsNotNone(runtime_store)
            self.assertEqual(
                str(getattr(runtime_store, "__file__", "")),
                str(HERMES_PKG / "tools/runtime_store.py"),
            )
            # orchestration lazy-imports runtime_store when checking .runtime fallback
            gate = mod._artifact_gate_with_runtime(
                "librarian",
                Path("/nonexistent/workspace"),
                "20260709120000",
                {"gate_ok": False, "errors": ["missing"]},
            )
            self.assertIn("gate_ok", gate)
        finally:
            for key, val in saved.items():
                if val is not None:
                    sys.modules[key] = val
                else:
                    sys.modules.pop(key, None)

    def test_board_status_after_stale_orchestration_module(self) -> None:
        """Gateway may cache orchestration before runtime_store overlay existed."""
        plugin = _load_digest_tools_plugin()
        stale = types.ModuleType("tools.orchestration")

        def _fake_board_status(*, brief: bool = False):
            from tools.runtime_store import run_dir  # noqa: F401 — exercise lazy import

            return {"ok": True, "phase": "idle", "brief": brief}

        stale.board_status = _fake_board_status  # type: ignore[attr-defined]
        stale.__file__ = str(HERMES_PKG / "tools/orchestration.py")
        saved = sys.modules.get("tools.orchestration")
        sys.modules["tools.orchestration"] = stale
        sys.modules.pop("tools.runtime_store", None)
        try:
            out = plugin.digest_board_status_json({"brief": True})
            data = json.loads(out)
            self.assertTrue(data.get("ok"), data)
            self.assertIsNotNone(sys.modules.get("tools.runtime_store"))
        finally:
            if saved is not None:
                sys.modules["tools.orchestration"] = saved
            else:
                sys.modules.pop("tools.orchestration", None)


if __name__ == "__main__":
    unittest.main()
