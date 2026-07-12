#!/usr/bin/env python3
"""Run full workflow evaluation and capture metrics.

This script:
1. Runs the workflow with real sources
2. Validates the brief artifact  
3. Compares against baseline (app/index.json)
4. Outputs eval metrics for documentation

Usage:
    python eval_run.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
_REPO_ROOT = Path(__file__).parent
_SRC = _REPO_ROOT / "agentic" / "kaggle_ai_agents" / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from kaggle_ai_agents.workflow import run_daily_brief
from kaggle_ai_agents.models import DailyBrief


def run_evaluation() -> dict:
    """Run full workflow and evaluate output.
    
    Returns:
        dict with metrics: cards_count, sources_count, eval_exit_code, baseline_gap_pct, etc.
    """
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "run_status": "PENDING",
        "cards_count": 0,
        "sources_fetched": 0,
        "validation_passed": False,
        "baseline_gap_pct": None,
        "baseline_within_threshold": False,
        "errors": [],
    }
    
    try:
        # Phase 1: Run workflow with real sources
        print("Phase 1: Running workflow with real sources...")
        brief: DailyBrief = run_daily_brief(use_real_sources=True)
        metrics["cards_count"] = len(brief.cards)
        print(f"  ✅ Generated brief with {metrics['cards_count']} cards")
        
        # Phase 2: Validate brief schema
        print("Phase 2: Validating brief artifact...")
        
        # Serialize with Pydantic's JSON serializer to handle HttpUrl
        brief_json = brief.model_dump_json()
        with open("/tmp/brief_generated.json", "w") as f:
            f.write(brief_json)
        
        validate_script = (
            _REPO_ROOT
            / "agentic"
            / "kaggle_ai_agents"
            / "skills"
            / "artifact_validation"
            / "scripts"
            / "validate.py"
        )
        result = subprocess.run(
            [sys.executable, str(validate_script), "/tmp/brief_generated.json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        metrics["validation_passed"] = result.returncode == 0
        if metrics["validation_passed"]:
            print("  ✅ Brief schema valid")
        else:
            print(f"  ❌ Validation failed: {result.stderr}")
            metrics["errors"].append(f"Validation: {result.stderr}")
        
        # Phase 3: Compare against baseline
        print("Phase 3: Comparing against baseline...")
        baseline_script = (
            _REPO_ROOT
            / "agentic"
            / "kaggle_ai_agents"
            / "skills"
            / "baseline_eval"
            / "scripts"
            / "evaluate.py"
        )
        baseline_index = _REPO_ROOT / "app" / "index.json"
        
        result = subprocess.run(
            [sys.executable, str(baseline_script), "/tmp/brief_generated.json", str(baseline_index)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        # Parse eval output (if available)
        try:
            # Output is "FAIL: ..." or "PASS: ..." followed by JSON
            lines = result.stdout.strip().split('\n')
            json_start = 1 if lines[0].startswith(('FAIL:', 'PASS:')) else 0
            eval_output = json.loads('\n'.join(lines[json_start:]))
            if isinstance(eval_output, dict):
                metrics["baseline_gap_pct"] = eval_output.get("worst_gap_pct")
                metrics["baseline_within_threshold"] = result.returncode == 0
        except (json.JSONDecodeError, ValueError, IndexError):
            pass
        
        if result.returncode == 0:
            print(f"  ✅ Within baseline threshold")
        else:
            print(f"  ⚠️  Exceeds baseline threshold")
        
        metrics["run_status"] = "SUCCESS"
        
    except subprocess.TimeoutExpired:
        metrics["errors"].append("Workflow timed out (>30s)")
        metrics["run_status"] = "TIMEOUT"
    except Exception as e:
        metrics["errors"].append(str(e))
        metrics["run_status"] = "FAILED"
    
    return metrics


def format_results(metrics: dict) -> str:
    """Format metrics as markdown table row."""
    timestamp = metrics["timestamp"][:10]  # YYYY-MM-DD
    status = metrics["run_status"]
    cards = metrics["cards_count"]
    valid = "✅" if metrics["validation_passed"] else "❌"
    gap = f"{metrics['baseline_gap_pct']:.1f}%" if metrics["baseline_gap_pct"] is not None else "N/A"
    threshold = "✅ PASS" if metrics["baseline_within_threshold"] else "⚠️ EXCEEDS"
    
    return f"| {timestamp} | {status} | {cards} | {valid} | {gap} | {threshold} |"


if __name__ == "__main__":
    print("=" * 80)
    print("AI Digest PoC Evaluation Run")
    print("=" * 80)
    print()
    
    metrics = run_evaluation()
    
    print()
    print("=" * 80)
    print("Evaluation Summary")
    print("=" * 80)
    print(json.dumps(metrics, indent=2))
    print()
    print("Markdown row for evaluation_results.md:")
    print(format_results(metrics))
    print()
    
    sys.exit(0 if metrics["run_status"] == "SUCCESS" else 1)
