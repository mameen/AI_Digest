"""Track 3 metrics & exit criteria — side-by-side comparison, scorecard, gateway telemetry.

Per the Hermes archive criteria captured in docs/ARCHIVE_NOTES.md:
1. Side-by-side diagnostic waterfall comparing kanban → render vs batch → render
2. Automated scorecard: ≥55 stories, 11/11 categories, ≤5% provenance gap
3. Telemetry log capturing gateway health at each run
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Gateway telemetry
# ---------------------------------------------------------------------------

@dataclass
class GatewayTelemetryEntry:
    """Single gateway health check record."""
    timestamp: str = field(default_factory=_utc_now)
    healthy: bool = False
    message: str = ""
    path_chosen: str = ""  # "kanban" or "batch"


@dataclass
class GatewayTelemetryLog:
    """Append-only gateway health log for a single run."""
    prefix: str
    entries: list[GatewayTelemetryEntry] = field(default_factory=list)

    @property
    def path(self) -> Path:
        return Path(__file__).resolve().parents[2] / ".runtime" / "telemetry" / f"{self.prefix}.gateway.jsonl"

    def append(self, entry: GatewayTelemetryEntry) -> None:
        self.entries.append(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": entry.timestamp,
                "healthy": entry.healthy,
                "message": entry.message,
                "path_chosen": entry.path_chosen,
            }) + "\n")

    @classmethod
    def load(cls, prefix: str) -> GatewayTelemetryLog:
        log_path = Path(__file__).resolve().parents[2] / ".runtime" / "telemetry" / f"{prefix}.gateway.jsonl"
        entries: list[GatewayTelemetryEntry] = []
        if log_path.exists():
            for line in log_path.read_text(encoding="utf-8").strip().split("\n"):
                if line.strip():
                    d = json.loads(line)
                    entries.append(GatewayTelemetryEntry(**d))
        return cls(prefix=prefix, entries=entries)

    @property
    def summary(self) -> dict[str, Any]:
        total = len(self.entries)
        healthy = sum(1 for e in self.entries if e.healthy)
        unhealthy = total - healthy
        kanban_count = sum(1 for e in self.entries if e.path_chosen == "kanban")
        batch_count = sum(1 for e in self.entries if e.path_chosen == "batch")
        return {
            "prefix": self.prefix,
            "total_checks": total,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "health_rate_pct": round(100 * healthy / total, 1) if total else 0,
            "kanban_dispatches": kanban_count,
            "batch_fallbacks": batch_count,
        }


# ---------------------------------------------------------------------------
# Scorecard — parity gate between kanban and batch paths
# ---------------------------------------------------------------------------

@dataclass
class StoryCount:
    kanban: int = 0
    batch: int = 0

    @property
    def match(self) -> bool:
        return self.kanban == self.batch

    @property
    def gap_pct(self) -> float:
        if self.kanban == 0 and self.batch == 0:
            return 0.0
        base = max(self.kanban, self.batch)
        return abs(self.kanban - self.batch) / base * 100 if base else 0


@dataclass
class CategoryCoverage:
    kanban: set[str] = field(default_factory=set)
    batch: set[str] = field(default_factory=set)

    @property
    def all_categories(self) -> set[str]:
        return self.kanban | self.batch

    @property
    def covered(self) -> set[str]:
        return self.kanban & self.batch

    @property
    def gap_pct(self) -> float:
        total = len(self.all_categories)
        if total == 0:
            return 0.0
        missing = total - len(self.covered)
        return missing / total * 100


@dataclass
class ProvenanceMatch:
    """Compare provenance tokens between two digests."""
    kanban_tokens: set[str] = field(default_factory=set)
    batch_tokens: set[str] = field(default_factory=set)

    @property
    def matched(self) -> int:
        return len(self.kanban_tokens & self.batch_tokens)

    @property
    def only_kanban(self) -> int:
        return len(self.kanban_tokens - self.batch_tokens)

    @property
    def only_batch(self) -> int:
        return len(self.batch_tokens - self.kanban_tokens)

    @property
    def gap_pct(self) -> float:
        total = len(self.kanban_tokens | self.batch_tokens)
        if total == 0:
            return 0.0
        mismatched = self.only_kanban + self.only_batch
        return mismatched / total * 100


@dataclass
class ScorecardResult:
    story_count: StoryCount = field(default_factory=StoryCount)
    category_coverage: CategoryCoverage = field(default_factory=CategoryCoverage)
    provenance_match: ProvenanceMatch = field(default_factory=ProvenanceMatch)

    @property
    def pass_story_count(self) -> bool:
        return self.story_count.gap_pct <= 5.0

    @property
    def pass_categories(self) -> bool:
        return self.category_coverage.gap_pct <= 5.0

    @property
    def pass_provenance(self) -> bool:
        return self.provenance_match.gap_pct <= 5.0

    @property
    def passed(self) -> bool:
        return self.pass_story_count and self.pass_categories and self.pass_provenance

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "story_count": {
                "kanban": self.story_count.kanban,
                "batch": self.story_count.batch,
                "gap_pct": round(self.story_count.gap_pct, 2),
                "pass": self.pass_story_count,
            },
            "category_coverage": {
                "all_categories": sorted(self.category_coverage.all_categories),
                "covered": sorted(self.category_coverage.covered),
                "missing": sorted(self.category_coverage.all_categories - self.category_coverage.covered),
                "gap_pct": round(self.category_coverage.gap_pct, 2),
                "pass": self.pass_categories,
            },
            "provenance_match": {
                "matched": self.provenance_match.matched,
                "only_kanban": self.provenance_match.only_kanban,
                "only_batch": self.provenance_match.only_batch,
                "gap_pct": round(self.provenance_match.gap_pct, 2),
                "pass": self.pass_provenance,
            },
        }


def extract_story_count(digest_json: dict[str, Any]) -> int:
    """Count stories in a digest JSON (works for both kanban and batch formats)."""
    # Top-level stories list
    top_stories = digest_json.get("stories", [])
    if isinstance(top_stories, list) and len(top_stories) > 0:
        return len(top_stories)
    # Nested under categories
    categories = digest_json.get("categories", [])
    total = 0
    for cat in categories:
        items = cat.get("stories", [])
        if isinstance(items, list):
            total += len(items)
    return total


def extract_categories(digest_json: dict[str, Any]) -> set[str]:
    """Extract category names from a digest JSON."""
    cats = set()
    for cat in digest_json.get("categories", []):
        name = cat.get("name", "") or cat.get("title", "")
        if name:
            cats.add(name)
    return cats


def extract_provenance_tokens(digest_json: dict[str, Any]) -> set[str]:
    """Extract provenance tokens from stories in a digest JSON."""
    tokens = set()
    for story in digest_json.get("stories", []):
        token = story.get("provenance", "") or story.get("trace", "")
        if token:
            tokens.add(token)
    # Also check categories → stories
    for cat in digest_json.get("categories", []):
        for story in cat.get("stories", []):
            token = story.get("provenance", "") or story.get("trace", "")
            if token:
                tokens.add(token)
    return tokens


def compute_scorecard(kanban_path: Path, batch_path: Path) -> ScorecardResult:
    """Load two digest JSONs and compute the parity scorecard."""
    kanban_data = json.loads(kanban_path.read_text(encoding="utf-8")) if kanban_path.exists() else {}
    batch_data = json.loads(batch_path.read_text(encoding="utf-8")) if batch_path.exists() else {}

    result = ScorecardResult()
    result.story_count.kanban = extract_story_count(kanban_data)
    result.story_count.batch = extract_story_count(batch_data)
    result.category_coverage.kanban = extract_categories(kanban_data)
    result.category_coverage.batch = extract_categories(batch_data)
    result.provenance_match.kanban_tokens = extract_provenance_tokens(kanban_data)
    result.provenance_match.batch_tokens = extract_provenance_tokens(batch_data)
    return result


# ---------------------------------------------------------------------------
# Side-by-side diagnostic comparison
# ---------------------------------------------------------------------------

@dataclass
class StageTiming:
    stage_name: str
    kanban_ms: float = 0.0
    batch_ms: float = 0.0

    @property
    def faster(self) -> str:
        if self.kanban_ms == 0 and self.batch_ms == 0:
            return "n/a"
        if self.kanban_ms < self.batch_ms:
            return "kanban"
        elif self.batch_ms < self.kanban_ms:
            return "batch"
        return "equal"

    @property
    def speedup_pct(self) -> float:
        base = max(self.kanban_ms, self.batch_ms)
        if base == 0:
            return 0.0
        diff = abs(self.kanban_ms - self.batch_ms) / base * 100
        return round(diff, 1)


@dataclass
class SideBySideComparison:
    """Compare kanban vs batch diagnostics side-by-side."""
    prefix_kanban: str = ""
    prefix_batch: str = ""
    stages: list[StageTiming] = field(default_factory=list)
    total_kanban_ms: float = 0.0
    total_batch_ms: float = 0.0
    scorecard: ScorecardResult = field(default_factory=ScorecardResult)

    @property
    def faster_path(self) -> str:
        if self.total_kanban_ms < self.total_batch_ms:
            return "kanban"
        elif self.total_batch_ms < self.total_kanban_ms:
            return "batch"
        return "equal"

    @property
    def speedup_pct(self) -> float:
        base = max(self.total_kanban_ms, self.total_batch_ms)
        if base == 0:
            return 0.0
        diff = abs(self.total_kanban_ms - self.total_batch_ms) / base * 100
        return round(diff, 1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prefix_kanban": self.prefix_kanban,
            "prefix_batch": self.prefix_batch,
            "faster_path": self.faster_path,
            "total_duration_ms": {
                "kanban": round(self.total_kanban_ms, 1),
                "batch": round(self.total_batch_ms, 1),
            },
            "speedup_pct": self.speedup_pct,
            "stages": [
                {
                    "stage": s.stage_name,
                    "kanban_ms": round(s.kanban_ms, 1),
                    "batch_ms": round(s.batch_ms, 1),
                    "faster": s.faster,
                    "speedup_pct": s.speedup_pct,
                }
                for s in self.stages
            ],
            "scorecard": self.scorecard.to_dict(),
        }


def load_diagnostics(prefix: str, diag_dir: Path) -> dict[str, Any] | None:
    """Load diagnostics JSON for a given prefix."""
    path = diag_dir / f"{prefix}.diagnostics.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def compare_diagnostics(
    kanban_diag: dict[str, Any] | None,
    batch_diag: dict[str, Any] | None,
    scorecard: ScorecardResult,
) -> SideBySideComparison:
    """Build side-by-side comparison from two diagnostics reports."""
    result = SideBySideComparison()
    result.scorecard = scorecard

    if kanban_diag:
        result.prefix_kanban = kanban_diag.get("prefix", "")
        result.total_kanban_ms = kanban_diag.get("totals", {}).get("llm_duration_ms", 0)
        # Also use total_duration_ms for wall time comparison
        result.total_kanban_ms = kanban_diag.get("total_duration_ms", result.total_kanban_ms)

    if batch_diag:
        result.prefix_batch = batch_diag.get("prefix", "")
        result.total_batch_ms = batch_diag.get("totals", {}).get("llm_duration_ms", 0)
        result.total_batch_ms = batch_diag.get("total_duration_ms", result.total_batch_ms)

    # Compare stages
    kanban_stages = {s["id"]: s for s in (kanban_diag.get("stages", []) or [])} if kanban_diag else {}
    batch_stages = {s["id"]: s for s in (batch_diag.get("stages", []) or [])} if batch_diag else {}

    all_stage_ids = set(kanban_stages.keys()) | set(batch_stages.keys())
    for stage_id in sorted(all_stage_ids):
        ks = kanban_stages.get(stage_id, {})
        bs = batch_stages.get(stage_id, {})
        timing = StageTiming(
            stage_name=stage_id,
            kanban_ms=ks.get("duration_ms", 0),
            batch_ms=bs.get("duration_ms", 0),
        )
        result.stages.append(timing)

    return result


# ---------------------------------------------------------------------------
# T3-C exit criteria evaluation
# ---------------------------------------------------------------------------

@dataclass
class ExitCriteriaResult:
    """Whether Track 3 should continue or archive."""
    passed: bool = False
    reasons: list[str] = field(default_factory=list)
    scorecard: ScorecardResult = field(default_factory=ScorecardResult)
    comparison: SideBySideComparison = field(default_factory=SideBySideComparison)

    @property
    def should_archive(self) -> bool:
        return not self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "should_archive": self.should_archive,
            "reasons": self.reasons,
            "scorecard": self.scorecard.to_dict(),
            "comparison": self.comparison.to_dict(),
        }


def evaluate_exit_criteria(
    scorecard: ScorecardResult,
    comparison: SideBySideComparison,
) -> ExitCriteriaResult:
    """Evaluate Hermes reference-runtime exit criteria."""
    result = ExitCriteriaResult(
        scorecard=scorecard,
        comparison=comparison,
    )

    reasons = []

    if not scorecard.pass_story_count:
        reasons.append(
            f"Story count gap {scorecard.story_count.gap_pct:.1f}% exceeds 5% threshold "
            f"(kanban={scorecard.story_count.kanban}, batch={scorecard.story_count.batch})"
        )

    if not scorecard.pass_categories:
        missing = scorecard.category_coverage.all_categories - scorecard.category_coverage.covered
        reasons.append(
            f"Category coverage gap {scorecard.category_coverage.gap_pct:.1f}% exceeds 5% threshold "
            f"(missing: {sorted(missing)})"
        )

    if not scorecard.pass_provenance:
        reasons.append(
            f"Provenance gap {scorecard.provenance_match.gap_pct:.1f}% exceeds 5% threshold "
            f"(only_kanban={scorecard.provenance_match.only_kanban}, only_batch={scorecard.provenance_match.only_batch})"
        )

    result.passed = len(reasons) == 0
    result.reasons = reasons
    return result


# ---------------------------------------------------------------------------
# Convenience: run full T3-C evaluation from filesystem paths
# ---------------------------------------------------------------------------

def run_t3c_evaluation(
    kanban_diag_dir: Path,
    batch_diag_dir: Path,
    kanban_report_path: Path,
    batch_report_path: Path,
    prefix_kanban: str = "",
    prefix_batch: str = "",
) -> ExitCriteriaResult:
    """Full T3-C evaluation: scorecard + side-by-side + exit criteria."""
    # Scorecard from digest JSONs
    scorecard = compute_scorecard(kanban_report_path, batch_report_path)

    # Side-by-side from diagnostics
    kanban_diag = load_diagnostics(prefix_kanban or "", kanban_diag_dir)
    batch_diag = load_diagnostics(prefix_batch or "", batch_diag_dir)
    comparison = compare_diagnostics(kanban_diag, batch_diag, scorecard)

    # Exit criteria
    return evaluate_exit_criteria(scorecard, comparison)
