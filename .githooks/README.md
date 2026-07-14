# Git hooks — maintainer-only commit attribution + security scans

## Install (once per clone)

```bash
pip install -r requirements-dev.txt
# optional: brew install betterleaks
./.githooks/install.sh
```

## Pre-commit

- **`audit_secrets.py --staged`** — Betterleaks/Gitleaks, or detect-secrets fallback

## Ignore files

| File | Purpose |
|---|---|
| **`.piiignore`** | Scanner exemptions (gitignore syntax) |
| **`.ignorepii`** | Optional alias — merged with `.piiignore` |
| **`.gitleaksignore`** | Secret scanner allowlist (Gitleaks standard) |
| **`.secrets.baseline`** | detect-secrets brownfield baseline |

`.kb/` and `.runtime/` are gitignored and listed in `.piiignore`. They are still
**blocked** if accidentally staged.

## Manual audit

```bash
python scripts/audit_secrets.py --all
```
