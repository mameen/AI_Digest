"""Deploy into app/ — fixture-backed, no mocks."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from lib.deploy_app import (
    app_root,
    execute_deploy,
    list_deployable_prefixes,
    plan_deploy,
    prefixes_missing_from_app,
    rebuild_app_archives,
    resolve_source,
)
from lib.paths import REPO_ROOT


class DeployApp(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmpdir.name)
        self.pipeline = self.repo / "llm_pipeline"
        self.reports = self.pipeline / "reports"
        self.reports.mkdir(parents=True)
        self.diagnostics = self.pipeline / "diagnostics"
        self.diagnostics.mkdir(parents=True)
        (self.repo / "llm_pipeline" / "assets").mkdir(parents=True)
        (self.repo / "llm_pipeline" / "assets" / "ademiry.jpg").write_bytes(b"jpeg")

        sample = {
            "meta": {"date": "2026-07-07", "generator_version": "0.5.20260707120000"},
            "categories": {},
        }
        (self.reports / "20260707120000.json").write_text(json.dumps(sample), encoding="utf-8")
        (self.reports / "20260707120000.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
        (self.diagnostics / "20260707120000.diagnostics.json").write_text("{}", encoding="utf-8")

        vendor_scripts = REPO_ROOT / "llm_pipeline" / "vendor" / "ai-news-digest" / "scripts"
        dest_vendor = self.repo / "llm_pipeline" / "vendor" / "ai-news-digest" / "scripts"
        dest_vendor.mkdir(parents=True)
        for name in ("_report_utils.py", "build_frame.py"):
            src = vendor_scripts / name
            if src.is_file():
                shutil.copy2(src, dest_vendor / name)

        cfg_src = REPO_ROOT / "llm_pipeline" / "config.yaml"
        if cfg_src.is_file():
            shutil.copy2(cfg_src, self.pipeline / "config.yaml")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_list_deployable_prefixes(self) -> None:
        self.assertEqual(list_deployable_prefixes(self.reports), ["20260707120000"])

    def test_auto_skips_existing(self) -> None:
        source = resolve_source("pipeline", self.repo)
        app_reports = app_root(self.repo) / "reports"
        app_reports.mkdir(parents=True)
        shutil.copy2(self.reports / "20260707120000.json", app_reports / "20260707120000.json")
        shutil.copy2(self.reports / "20260707120000.html", app_reports / "20260707120000.html")
        self.assertEqual(prefixes_missing_from_app(source, self.repo), [])

    def test_one_day_deploy_creates_app_tree(self) -> None:
        plan = plan_deploy(
            source_kind="pipeline",
            mode="one-day",
            prefix="20260707120000",
            dry_run=False,
            repo=self.repo,
        )
        manifest = execute_deploy(plan, self.repo)
        app = app_root(self.repo)
        self.assertEqual(manifest["prefixes"], ["20260707120000"])
        self.assertEqual(manifest["source"], "llm_pipeline")
        self.assertTrue((app / "reports" / "20260707120000.html").is_file())
        self.assertTrue((app / "index" / "index.html").is_file())
        self.assertTrue((app / "index.json").is_file())
        self.assertTrue((app / "reports" / "index.html").is_file())
        self.assertTrue((app / "assets" / "ademiry.jpg").is_file())

    def test_rebuild_app_archives_index_json(self) -> None:
        app = app_root(self.repo)
        shutil.copytree(self.reports, app / "reports", dirs_exist_ok=True)
        rebuild_app_archives(self.repo, dry_run=False)
        index = json.loads((app / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(index["latest"], "20260707120000")
        self.assertEqual(len(index["digests"]), 1)
        self.assertEqual(
            (app / "index.json").read_text(encoding="utf-8"),
            (app / "index" / "index.json").read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
