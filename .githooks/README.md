# Git hooks — maintainer-only commit attribution + security scans

## Install (once per clone)

```bash
pip install -r requirements-dev.txt
python -m spacy download en_core_web_sm
# optional: brew install betterleaks
./.githooks/install.sh
```

## Pre-commit (three layers)

1. **`check_secrets.py --staged`** — fast blocked paths, tokens, home paths
2. **`audit_pii.py --staged`** — Microsoft Presidio PII/PHI
3. **`audit_secrets.py --staged`** — Betterleaks/Gitleaks, or detect-secrets fallback

## Ignore files

| File | Purpose |
|---|---|
| **`.piiignore`** | PII audit exemptions (gitignore syntax) |
| **`.ignorepii`** | Optional alias — merged with `.piiignore` |
| **`.gitleaksignore`** | Secret scanner allowlist (Gitleaks standard) |
| **`.secrets.baseline`** | detect-secrets brownfield baseline |

`.kb/` and `.runtime/` are gitignored and listed in `.piiignore`. They are still
**blocked** if accidentally staged.

## Manual audit

```bash
python scripts/check_secrets.py --all
python scripts/audit_pii.py --all
python scripts/audit_secrets.py --all
```
