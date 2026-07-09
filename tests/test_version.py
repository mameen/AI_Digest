"""Version surfacing: no mocks.

Asserts the MAJOR.MINOR release line, the ``generator_version`` helper, the
footer version span, and that a published report carries a well-formed
``generator_version`` whose third segment is the report's own run prefix.

A committed report keeps the version that *produced* it (reports are traced by
date/prefix, never re-stamped to the current code line), so the published-report
check asserts format + prefix-traceability rather than equality with the current
``__version__``.
"""

from __future__ import annotations

import json
import re
import unittest

from lib.paths import LLM_PIPELINE_ROOT
from pipeline import __version__, generator_version
from pipeline.site_footer import site_footer_html

REPORT = LLM_PIPELINE_ROOT / "reports" / "20260630120000.json"

_RELEASE_LINE = re.compile(r"^\d+\.\d+$")
_BUILD_ID = re.compile(r"^\d+\.\d+\.\d{14}$")


class Version(unittest.TestCase):
    def test_version_is_release_line(self) -> None:
        self.assertRegex(__version__, _RELEASE_LINE)

    def test_generator_version_appends_prefix_as_third_segment(self) -> None:
        self.assertEqual(
            generator_version("20260630120000"), f"{__version__}.20260630120000"
        )
        self.assertRegex(generator_version("20260630120000"), _BUILD_ID)

    def test_generator_version_without_prefix_is_bare_release_line(self) -> None:
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
        # Decoupled from the current release line: a report keeps the version
        # that produced it. Assert the release-line shape + that the third
        # segment is the report's own run prefix (date traceability).
        release, _, prefix = gv.rpartition(".")
        self.assertRegex(release, _RELEASE_LINE)
        self.assertEqual(prefix, data["filename_prefix"])


if __name__ == "__main__":
    unittest.main()
