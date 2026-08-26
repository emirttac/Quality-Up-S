#!/bin/bash
set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1

# Prefer python.org /usr/local when present (Tk-enabled); else python3 on PATH.
BOOTSTRAP=""
for candidate in /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3 python3; do
  if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
    if "$candidate" -c "import tkinter" >/dev/null 2>&1; then
      BOOTSTRAP="$candidate"
      break
    fi
  fi
done

if [ -z "$BOOTSTRAP" ]; then
  echo "Quality Up'S needs a Tk-enabled Python 3."
  echo "On macOS install from https://www.python.org/downloads/"
  echo
  read -r -p "Press Enter to close…"
  exit 1
fi

PY="$ROOT/.venv/bin/python3"
NEED_SETUP=0

if [ ! -x "$PY" ]; then
  NEED_SETUP=1
elif ! "$PY" -c "import numpy" >/dev/null 2>&1; then
  NEED_SETUP=1
fi

if [ "$NEED_SETUP" -eq 1 ]; then
  echo "Setting up Quality Up'S environment…"
  if [ ! -x "$PY" ]; then
    echo "Creating virtual environment…"
    "$BOOTSTRAP" -m venv "$ROOT/.venv" || {
      echo "Failed to create .venv"
      read -r -p "Press Enter to close…"
      exit 1
    }
  fi
  echo "Installing dependencies from requirements.txt…"
  "$PY" -m pip install --upgrade pip || {
    echo "pip upgrade failed."
    read -r -p "Press Enter to close…"
    exit 1
  }
  "$PY" -m pip install -r "$ROOT/requirements.txt" || {
    echo "Dependency install failed."
    read -r -p "Press Enter to close…"
    exit 1
  }
  if ! "$PY" -c "import numpy" >/dev/null 2>&1; then
    echo "numpy is still missing after install. Check the errors above."
    read -r -p "Press Enter to close…"
    exit 1
  fi
  echo "Setup complete."
  echo
fi

"$PY" "$ROOT/main.py"
status=$?
if [ "$status" -ne 0 ]; then
  echo
  echo "Quality Up'S closed with an error ($status)."
  read -r -p "Press Enter to close…"
fi
exit "$status"
