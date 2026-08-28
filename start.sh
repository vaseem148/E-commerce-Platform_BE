#!/usr/bin/env bash
#
# One-command dev startup for the Nexa Commerce API (macOS / Linux).
#
# Creates the virtual environment and installs dependencies on first run,
# seeds the demo database if it is empty, then starts the API on port 8000.
#
# Usage:
#   ./start.sh                 # start on 127.0.0.1:8000
#   PORT=8080 ./start.sh       # different port
#   RESEED=1 ./start.sh        # rebuild the demo dataset first

set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
API_HOST="${API_HOST:-127.0.0.1}"
RESEED="${RESEED:-0}"

cyan=$'\033[36m'; green=$'\033[32m'; yellow=$'\033[33m'
red=$'\033[31m';  dim=$'\033[2m';    reset=$'\033[0m'

printf '\n  %sNexa Commerce API%s\n' "$cyan" "$reset"
printf '  %s-----------------%s\n' "$dim" "$reset"

# --- Locate a Python interpreter -------------------------------------------
BOOTSTRAP_PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    BOOTSTRAP_PYTHON="$candidate"
    break
  fi
done

if [ -z "$BOOTSTRAP_PYTHON" ]; then
  printf '  %sPython 3.10+ was not found on PATH. Install it from https://python.org%s\n' "$red" "$reset"
  exit 1
fi

VENV_PYTHON=".venv/bin/python"

# --- Create the venv on first run ------------------------------------------
if [ ! -x "$VENV_PYTHON" ]; then
  printf '  %sCreating virtual environment (.venv)...%s\n' "$yellow" "$reset"
  "$BOOTSTRAP_PYTHON" -m venv .venv

  printf '  %sInstalling dependencies...%s\n' "$yellow" "$reset"
  "$VENV_PYTHON" -m pip install --upgrade pip --quiet
  "$VENV_PYTHON" -m pip install -r requirements.txt
else
  # Cheap guard in case requirements changed since the venv was built.
  if ! "$VENV_PYTHON" -c "import fastapi, uvicorn, sqlalchemy, jwt, pydantic_settings" >/dev/null 2>&1; then
    printf '  %sInstalling missing dependencies...%s\n' "$yellow" "$reset"
    "$VENV_PYTHON" -m pip install -r requirements.txt
  fi
fi

# --- Seed the database ------------------------------------------------------
if [ "$RESEED" = "1" ]; then
  printf '  %sRebuilding the demo dataset (--force)...%s\n' "$yellow" "$reset"
  "$VENV_PYTHON" seed.py --force
elif [ ! -f "nexa.db" ]; then
  printf '  %sSeeding the demo dataset...%s\n' "$yellow" "$reset"
  "$VENV_PYTHON" seed.py --force
fi

# --- Run --------------------------------------------------------------------
printf '\n'
printf '  %sAPI    http://%s:%s%s\n'      "$green" "$API_HOST" "$PORT" "$reset"
printf '  %sDocs   http://%s:%s/docs%s\n' "$green" "$API_HOST" "$PORT" "$reset"
printf '\n'
printf '  %sDemo accounts%s\n'                          "$dim" "$reset"
printf '  %s  admin     admin@nexa.com / Admin@123%s\n' "$dim" "$reset"
printf '  %s  customer  demo@nexa.com / Demo@123%s\n'   "$dim" "$reset"
printf '\n'
printf '  %sThe frontend expects this API on http://localhost:8000%s\n' "$dim" "$reset"
printf '  %sStart it separately with:  cd ../ep_frontend && ./start.sh%s\n' "$dim" "$reset"
printf '\n'
printf '  %sCtrl+C to stop.%s\n\n' "$dim" "$reset"

exec "$VENV_PYTHON" run.py --host "$API_HOST" --port "$PORT"
