"""Version surfacing: no mocks.

Asserts the SemVer core, the ``generator_version`` build-id helper, the footer
version span, and that the published 6/30 report carries a well-formed
``generator_version`` (SemVer core + 14-digit run prefix).
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from pipeline import __version__, generator_version
from pipeline.site_footer import site_footer_html

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "20260630120000.json"

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
_BUILD_ID = re.compile(r"^\d+\.\d+\.\d+\+\d{14}$")


class Version(unittest.TestCase):
    def test_version_is_semver_core(self) -> None:
        self.assertRegex(__version__, _SEMVER)

    def test_generator_version_appends_prefix_as_build_metadata(self) -> None:
        self.assertEqual(
            generator_version("20260630120000"), f"{__version__}+20260630120000"
        )
        self.assertRegex(generator_version("20260630120000"), _BUILD_ID)

    def test_generator_version_without_prefix_is_bare_semver(self) -> None:
        self.assertEqual(generator_version(""), __version__)


class Footer(unittest.TestCase):
    def test_footer_shows_version(self) -> None:
        html = site_footer_html({"site": {"author_short": "Tester"}})
        self.assertIn("site-footer-version", html)
        self.assertIn(f"v{__version__}", html)


class PublishedReport(unittest.TestCase):
    def test_report_json_carries_well_formed_generator_version(self) -> None:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        gv = data.get("generator_version")
        self.assertIsNotNone(gv, "published report is missing generator_version")
        self.assertRegex(gv, _BUILD_ID)
        # Build id embeds the report's own run prefix.
        self.assertEqual(gv, generator_version(data["filename_prefix"]))


if __name__ == "__main__":
    unittest.main()
