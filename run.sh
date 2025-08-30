#!/usr/bin/env bash
set -euo pipefail

# Resolve script path without relying on interactive shell vars
SCRIPT="$0"
if [ -L "$SCRIPT" ]; then
  while [ -L "$SCRIPT" ]; do
    LINK_TARGET="$(readlink "$SCRIPT")"
    case "$LINK_TARGET" in
      /*) SCRIPT="$LINK_TARGET" ;;
      *)  SCRIPT="$(dirname "$SCRIPT")/$LINK_TARGET" ;;
    esac
  done
fi
ROOT="$(cd -P -- "$(dirname -- "$SCRIPT")" && pwd)"
APP_DIR="$ROOT/src"
export PYTHONPATH="$APP_DIR:${PYTHONPATH:-}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"

# Ignore venv + pyc so reloads don’t loop
export WATCHFILES_IGNORE="${WATCHFILES_IGNORE:-.venv/**,**/__pycache__/**,**/*.pyc,**/*.pyo}"

echo "→ Starting Tobyworld Mirror V3 @ http://$HOST:$PORT  (app=tobyworld.api.server:app)"
exec uvicorn --app-dir "$APP_DIR" tobyworld.api.server:app \
  --host "$HOST" --port "$PORT" \
  --reload --reload-dir "$APP_DIR" \
  --reload-exclude ".venv/*" \
  --reload-exclude "**/__pycache__/*" \
  --reload-exclude "**/*.pyc" \
  --reload-exclude "**/*.pyo"
