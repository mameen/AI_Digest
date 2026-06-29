"""Digest run date and history window helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


@dataclass(frozen=True)
class RunWindow:
    """Digest run date and editorial lookback window."""

    start: date
    history_days: int
    prefix: str

    @property
    def history_from(self) -> date:
        return self.start - timedelta(days=self.history_days)

    @property
    def generated_at(self) -> str:
        noon = datetime(
            self.start.year,
            self.start.month,
            self.start.day,
            12,
            0,
            0,
            tzinfo=timezone.utc,
        )
        return noon.strftime("%Y-%m-%dT%H:%M:%SZ")

    def label(self) -> str:
        return f"{self.history_from.isoformat()} -> {self.start.isoformat()} ({self.history_days}d)"


_DATE_RE = re.compile(r"^(\d{4})-?(\d{2})-?(\d{2})$")
_PREFIX_RE = re.compile(r"^(\d{14})$")


def parse_start(value: str | None) -> date:
    """Parse --start (YYYY-MM-DD, YYYYMMDD, or 14-digit prefix); default today UTC."""
    if value is None:
        return datetime.now(timezone.utc).date()

    value = value.strip()
    m = _PREFIX_RE.match(value)
    if m:
        pfx = m.group(1)
        return date(int(pfx[0:4]), int(pfx[4:6]), int(pfx[6:8]))

    m = _DATE_RE.match(value)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    raise ValueError(f"invalid start date {value!r}; use YYYY-MM-DD or YYYYMMDD")


def prefix_for_start(start: date) -> str:
    """Canonical digest prefix: noon UTC on the run date."""
    return start.strftime("%Y%m%d") + "120000"


def build_run_window(start: str | None, history_days: int) -> RunWindow:
    if history_days < 0:
        raise ValueError(f"history must be >= 0, got {history_days}")
    day = parse_start(start)
    return RunWindow(start=day, history_days=history_days, prefix=prefix_for_start(day))
