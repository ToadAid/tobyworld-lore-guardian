#!/usr/bin/env bash
set -euo pipefail

# Resolve script path (works with symlinks)
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
PORT="${PORT:-8081}"

# Ignore venv + pyc so reloads don’t loop
export WATCHFILES_IGNORE="${WATCHFILES_IGNORE:-.venv/**,**/__pycache__/**,**/*.pyc,**/*.pyo}"

# Build reload flags based on DEV_NO_RELOAD
if [[ "${DEV_NO_RELOAD:-}" == "1" ]]; then
  RELOAD_FLAGS=()
  MODE="(no-reload)"
else
  RELOAD_FLAGS=(--reload --reload-dir "$APP_DIR" \
                --reload-exclude ".venv/*" --reload-exclude "**/__pycache__/*" \
                --reload-exclude "**/*.py[co]")
  MODE="(reload)"
fi

echo "→ Starting Tobyworld Mirror V3 @ http://$HOST:$PORT  $MODE  (app=tobyworld.api.server:app)"
exec uvicorn --app-dir "$APP_DIR" tobyworld.api.server:app \
  --host "$HOST" --port "$PORT" \
  "${RELOAD_FLAGS[@]}"
