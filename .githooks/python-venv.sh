# shellcheck shell=sh
# Resolve a python interpreter that carries the security-scanner deps.
# Git GUI clients launch hooks without the shell's activated virtualenv, so a
# bare python3 can resolve to a system interpreter that lacks presidio-analyzer.
# Prefer the repo venv; fall back to python3. Callers must cd to the repo root
# before sourcing (the hooks already do).
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
  PY="$VIRTUAL_ENV/bin/python"
else
  PY="python3"
fi
