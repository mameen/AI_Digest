# Day 4 Example - Secure Agentic Coding (Clean Capture)

Source codelab:
https://codelabs.developers.google.com/secure-agentic-coding

Last updated: Jun 17, 2026
Authors: Aron Eidelman, Sita Lakshmi Sangameswaran

## About This Codelab

This lab is part of Kaggle's 5-Day AI Agents: Intensive Vibe Coding Course with Google.

Event site:
https://www.kaggle.com/competitions/5-day-ai-agents-intensive-vibecoding-course-with-google

You build a retail web app with an integrated AI Shopping Assistant using ADK, and apply secure test-driven development in Antigravity IDE.

Core theme: shift security left at code inception rather than treating security as a final gate.

## What You Do (Clean List)

1. Scaffold an ADK 2.0 shopping assistant with Antigravity and `agents-cli`.
2. Define secure coding standards in a persistent `CONTEXT.md` file.
3. Build and invoke a workspace STRIDE threat-modeling skill.
4. Enforce security guardrails during TDD plan phase.
5. Write outcome-based security tests in `pytest`.
6. Configure pre-commit hooks with Semgrep for local remediation loops.

## What You Need

1. Web browser (for example, Chrome)
2. Familiarity with Python, Pytest, and terminal basics
3. Antigravity IDE installed
   - https://antigravity.google/docs/home
4. `uv` installed
   - https://docs.astral.sh/uv/getting-started/installation/
5. Git CLI installed (local use; GitHub account not required)
   - https://github.com/git-guides/install-git

Estimated time: about 60 minutes.

## Security Pattern Highlights

1. Persistent secure context (`CONTEXT.md`) defines project guardrails.
2. STRIDE threat modeling is integrated into daily coding flow.
3. Security checks run as pre-commit automation, not manual afterthought.
4. Local remediation loop keeps fixes close to code changes.

## Authentication and Environment (Local Concept Demo)

This lab demonstrates local guardrails and pre-commit remediation loops.
No Google Cloud auth or GitHub connection is required.

For model access, export Gemini credentials in terminal:

```bash
export MODEL_KEY_ENV_VAR="your_model_key_here"
export GOOGLE_GENAI_USE_ENTERPRISE=FALSE
```

## Day 4 Relevance to This Kaggle POC

Map this codelab directly into our Day 4 docs:

1. Threat model -> `day_4/threat_model.md`
2. Security controls -> `day_4/security_controls.md`
3. Evaluation plan -> `day_4/evaluation_plan.md`
4. Test matrix -> `day_4/test_matrix.md`

Additions to enforce:

1. Security checks run before publish steps.
2. Validation and baseline parity checks gate outputs.
3. Sensitive values stay in environment variables, never in repo files.

## Step 2 - Setup Workspace and Toolchain (Clean Capture)

Goal: initialize a local workspace and install the agent toolchain for secure development.

### Practical Notes

1. Antigravity may show plans/popups before running commands. Review and approve to continue.
2. If model quota is exhausted, switch to another available model in Antigravity.

### Prompt to Antigravity (Cleaned)

"Help me set up my local project workspace. Please:
1) Create a new directory `~/secure-agent-lab`, navigate into it, initialize a Git repository, and configure my local Git identity (user.name: \"Kaggle Student\", user.email: \"student@example.com\").
2) Create and activate a Python virtual environment using `uv`.
3) Install and verify the `agents-cli` toolchain by running `uvx google-agents-cli setup` and `agents-cli info`."

### Expected Outcome

1. Clean local Git repository initialized.
2. Python environment created with `uv`.
3. `agents-cli` setup completed and `agents-cli info` returns environment details.
4. ADK companion skills become available in IDE tooling.

## Step 6 - Configure Local Gating Hooks (Clean Capture)

Goal: block insecure code and secret leakage before commits by adding automated local gates.

### A. Git Pre-Commit Hook + Custom Semgrep Rule

Why custom rule:

1. Default `semgrep --config auto` may miss low-confidence mock or hyphenated key formats.
2. A direct regex rule reliably catches hardcoded Google-style API key prefixes.

Prompt to Antigravity (rule file):

"Create a custom Semgrep rules file `shopping-assistant/.semgrep/rules.yaml` with a rule to detect hardcoded Google API key prefixes (regex `AIzaSy[A-Za-z0-9_\\-]*`). Configure it for Python files with ERROR severity and a clear warning message."

Representative output:

```yaml
# shopping-assistant/.semgrep/rules.yaml
rules:
   - id: detect-hardcoded-google-api-key
      pattern-regex: 'AIzaSy[A-Za-z0-9_\-]*'
      message: "Security Issue: Hardcoded Google API key prefix detected."
      languages:
         - python
      severity: ERROR
```

Prompt to Antigravity (pre-commit config):

"Create `shopping-assistant/.pre-commit-config.yaml` with local hooks (`end-of-file-fixer`, `trailing-whitespace`) and a Semgrep scan for Python files using `--error` and config path `shopping-assistant/.semgrep/rules.yaml` relative to repo root. Then run `pre-commit install`."

Representative output:

```yaml
# shopping-assistant/.pre-commit-config.yaml
repos:
   - repo: local
      hooks:
         - id: end-of-file-fixer
            name: End of File Fixer
            entry: end-of-file-fixer
            language: system
            types: [file]
         - id: trailing-whitespace
            name: Trailing Whitespace
            entry: trailing-whitespace-fixer
            language: system
            types: [file]
         - id: semgrep
            name: Semgrep Security Scan
            entry: semgrep --error --config shopping-assistant/.semgrep/rules.yaml
            language: system
            types: [python]
```

Important note:

1. `--error` is required. Without it, findings may not fail the commit.

Manual verification commands:

```bash
# from shopping-assistant/
uv run pre-commit run semgrep --all-files
uv run semgrep --error --config .semgrep/rules.yaml app/agent.py
```

### B. Built-in Antigravity Agent Hook (PreToolUse)

Purpose: intercept dangerous tool calls before shell execution.

Prompt to Antigravity (hooks config):

"Create `shopping-assistant/.agents/hooks.json` with a `PreToolUse` hook matching `run_command`, executing `python3 .agents/scripts/validate_tool_call.py`, timeout 10 seconds."

Representative output:

```json
{
   "enabled": true,
   "PreToolUse": [
      {
         "matcher": "run_command",
         "command": "python3 .agents/scripts/validate_tool_call.py",
         "timeout": 10
      }
   ]
}
```

Critical caution:

1. `matcher` is mandatory for safe interception behavior.

Prompt to Antigravity (validator script):

"Create `shopping-assistant/.agents/scripts/validate_tool_call.py` to read stdin tool context and block destructive commands like `rm -rf /`."

Representative output:

```python
import json
import sys


def main() -> None:
      try:
            context = json.load(sys.stdin)
            command = context.get("tool_args", {}).get("CommandLine", "")
            if "rm -rf /" in command or "mkfs" in command:
                  print("BLOCKED: Destructive command detected.", file=sys.stderr)
                  raise SystemExit(1)
            print("APPROVED: Command validation passed.")
            raise SystemExit(0)
      except Exception as err:
            print(f"Validation error: {err}", file=sys.stderr)
            raise SystemExit(1)


if __name__ == "__main__":
      main()
```

### Hook Trade-Offs (Clean Summary)

1. Git hooks
- Pros: run even when agent automation is non-interactive.
- Cons: bypassable with `--no-verify`.

2. Agent hooks
- Pros: block risky commands mid-trajectory.
- Cons: protect IDE tool flow, not all repo write paths.

Final security stance:

1. Local gates improve speed and developer behavior.
2. Remote CI/CD remains the final non-bypassable security barrier.

## Step 7 - Implement STRIDE Threat Modeling Skill (Clean Capture)

Goal: add a reusable local Antigravity skill that performs structured STRIDE assessments.

### Why This Step Matters

1. Skills package expert reasoning into reusable, on-demand modules.
2. Keeping security logic in `.agents/skills/` avoids bloating everyday prompt context.
3. STRIDE analysis can be rerun consistently at each implementation phase.

### Prompt to Antigravity (Create Skill)

"Create local skill directory `shopping-assistant/.agents/skills/stride-threat-model/` and a skill definition file `shopping-assistant/.agents/skills/stride-threat-model/SKILL.md` with STRIDE analysis instructions that produce `threat_model.md` in workspace root."

Representative `SKILL.md`:

```md
---
name: stride-threat-model
description: Performs a systematic STRIDE threat modeling assessment on the current project's codebase and architecture. Use this when starting a new implementation phase or reviewing existing components.
---

# STRIDE Threat Modeling Skill

## Goal
Guide the agent to analyze workspace structure, config files, and code files to produce a structured `threat_model.md` assessment.

## Instructions
1. Analyze system boundaries (entry points, workflows, prompts, data storage layers).
2. Perform STRIDE evaluation:
   - Spoofing
   - Tampering
   - Repudiation
   - Information Disclosure
   - Denial of Service
   - Elevation of Privilege
3. Output a structured `threat_model.md` in workspace root.
```

### Prompt to Antigravity (Run Skill)

"Run stride-threat-model on our shopping-assistant agent graph."

### Expected Outcome

1. Antigravity discovers local skill in `.agents/skills/`.
2. Skill instructions load on demand.
3. Agent graph (for example, `shopping-assistant/app/agent.py`) is analyzed.
4. Structured `threat_model.md` is generated at `shopping-assistant/` root.

### Integration Note for This Kaggle POC

Map generated threats directly into:

1. `day_4/threat_model.md`
2. `day_4/security_controls.md`
3. `day_4/test_matrix.md`

## Step 8 - Gate the TDD Plan Phase (Clean Capture)

Goal: force security-first reasoning before implementation by adding a planning gate in `.agents/CONTEXT.md`.

### Why This Step Matters

1. Plan-time security checks reduce late-stage rework.
2. The agent must surface exploit-oriented edge cases before code generation.
3. Human approval remains explicit before implementation starts.

### Prompt to Antigravity (Add Planning Gate)

"Append this to `shopping-assistant/.agents/CONTEXT.md`:

## TDD Planning Gate
During the Plan phase, you must decompose the workspace task into logical, modular stages. Every implementation plan MUST include a dedicated **Security Boundaries & Assertions** section outlining specific edge cases that could exploit the feature."

### Expected Outcome

1. `.agents/CONTEXT.md` is updated with the TDD planning gate rule.
2. Future build/refactor prompts enter a plan phase first.
3. Generated `implementation_plan.md` includes **Security Boundaries & Assertions**.
4. You must explicitly approve/proceed before code generation.

## Optional Validation - Test the Planning Gate

Use one of these prompts to confirm gate behavior:

1. "Plan a new agent tool `award_loyalty_points` that awards points to a user's account after a successful purchase."
2. "Plan a new agent tool `process_cart_checkout` that receives a cart ID and discount code, applies the discount, and processes the order."
3. "Plan a new agent tool `update_discount_status` that allows administrators to activate or deactivate discount codes in the store."

Expected validation:

1. Agent produces plan/checklist before code edits.
2. Security section calls out abuse scenarios (for example: race conditions, privilege escalation, negative values, input tampering).
3. No implementation starts until explicit approval.

## Step 9 - Write Isolated, Outcome-Based Tests (Clean Capture)

Goal: create robust security tests that validate behavior boundaries without fragile implementation-coupled mocks.

### Testing Principles

1. Assert outcomes, not interactions
- assert final outputs and state transitions
- avoid brittle mocks that depend on internal helper call order

2. Enforce strict guardrails
- validate business logic boundaries (single-use redemption, registered-user checks, invalid-code rejection)

### Prompt to Antigravity

"Use `agents-cli` and pytest to generate an outcome-based security test suite in `shopping-assistant/tests/test_agent.py`. Inspect `app/agent.py` and write tests to verify security boundaries and business guardrails for `redeem_discount`."

### Representative Test Shape

```python
import pytest

from app.agent import DISCOUNT_STORE, redeem_discount


@pytest.fixture(autouse=True)
def reset_store():
   DISCOUNT_STORE["WELCOME50"] = False
   DISCOUNT_STORE["SUMMER20"] = False
   yield
   DISCOUNT_STORE["WELCOME50"] = False
   DISCOUNT_STORE["SUMMER20"] = False


def test_discount_code_can_only_be_redeemed_once():
   first = redeem_discount("WELCOME50", "user_123")
   assert "Success" in first
   assert DISCOUNT_STORE["WELCOME50"] is True

   second = redeem_discount("WELCOME50", "user_456")
   assert "Error: Discount code has already been redeemed" in second


def test_discount_redemption_rejects_invalid_code():
   out = redeem_discount("INVALID999", "user_123")
   assert "Error: Invalid discount code" in out


def test_discount_redemption_rejects_guest_accounts():
   out = redeem_discount("SUMMER20", "guest_999")
   assert "Error: Registered user account required" in out
   assert DISCOUNT_STORE["SUMMER20"] is False
```

## Verify TDD GREEN Phase

Prompt to Antigravity:

"Run `uv run pytest tests/test_agent.py` on `shopping-assistant` to verify the security tests pass."

Expected outcome:

1. All tests pass in GREEN phase.
2. Runtime guardrails appear correct.
3. Next gate remains static analysis/pre-commit checks for secret leakage and insecure patterns.

## Step 10 - Verify Gating and Agent Self-Correction (Clean Capture)

Goal: validate that local security gates block unsafe commits and trigger an agent remediation loop before code is committed.

### Commit Hygiene Rule

1. Do not use `--no-verify`.
2. We want pre-commit hooks to run and block insecure changes.

### Commit Attempt (with hooks active)

```bash
cd ~/secure-agent-lab/shopping-assistant
git add .
uv run git commit -m "feat: implement shopping assistant agent"
```

Expected failure sample:

```text
Semgrep Security Scan....................................................Failed
- hookid: semgrep

   app/agent.py
   Security Issue: Hardcoded Google API key prefix detected.
```

### Self-Correction Loop (Expected)

1. Antigravity detects pre-commit failure in terminal output.
2. Using pre-commit remediation guidance in `.agents/CONTEXT.md`, it initiates refactor.
3. `app/agent.py` is updated to remove hardcoded key handling and read key securely.
4. Agent reruns tests (for example, `pytest`) to keep behavior green.
5. Agent retries commit after security fix.

### Success Criteria

1. Commit is blocked while vulnerability exists.
2. Refactor removes secret leakage pattern.
3. Tests remain green after fix.
4. Commit succeeds only after hooks pass.

### Why This Matters

1. Security feedback happens locally and immediately.
2. Agent remains accountable to deterministic local gates.
3. Vulnerable code is corrected before any remote push/CI stage.

## Step 11 - Run and Test the Agent Locally (Clean Capture)

Goal: validate the secured agent end-to-end in local playground using exported Gemini credentials.

### Runtime Prerequisite

Ensure API key is exported in current shell:

```bash
echo "$MODEL_KEY_ENV_VAR"
```

### Launch Playground

```bash
cd ~/secure-agent-lab/shopping-assistant
agents-cli playground
```

Expected server output:

```text
* Serving ADK Playground
* Running on http://127.0.0.1:8080/dev-ui/?app=app
```

### Interactive Validation Prompt

Use in playground chat:

"Can you redeem the discount code WELCOME50 for user user_123?"

### Expected Behavior

1. Agent executes model-driven logic for discount redemption flow.
2. Tool path attempts redemption against configured store logic.

### Variation Note

Generated implementations may differ across Antigravity runs.

If `user_123` is rejected as unregistered:

1. ask the agent which user IDs are registered
2. or inspect `app/agent.py`
3. retry with a valid registered user ID
