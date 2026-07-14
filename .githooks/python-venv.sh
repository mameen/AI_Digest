# shellcheck shell=sh
# Resolve a python interpreter that carries the security-scanner deps.
# Git GUI clients launch hooks without the shell's activated virtualenv, so a
# bare python3 can resolve to a system interpreter that lacks the scanner deps.
# Prefer the repo venv; fall back to python/python3. Callers must cd to the
# repo root before sourcing (the hooks already do).

# Windows-compatible venv paths (Git Bash / MSYS2)
if [ -x ".venv/Scripts/python.exe" ]; then
  PY=".venv/Scripts/python.exe"
elif [ -x "venv/Scripts/python.exe" ]; then
  PY="venv/Scripts/python.exe"
# Unix-style venv paths (Linux/macOS or WSL)
elif [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/Scripts/python.exe" ]; then
  PY="$VIRTUAL_ENV/Scripts/python.exe"
elif [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
  PY="$VIRTUAL_ENV/bin/python"
else
  # Fallback: try python3 first, then python (Windows often only has python)
  if command -v python3 >/dev/null 2>&1; then
    PY="python3"
  else
    PY="python"
  fi
fi
