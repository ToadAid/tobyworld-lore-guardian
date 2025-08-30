#!/usr/bin/env bash
set -euo pipefail

# --- project paths ---
ROOT="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT/src"
export PYTHONPATH="$APP_DIR:${PYTHONPATH:-}"

# --- server config ---
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"

# Avoid reload loops if you ever move venv inside project
export WATCHFILES_IGNORE="${WATCHFILES_IGNORE:-.venv/**,**/__pycache__/**,**/*.pyc,**/*.pyo}"

echo "→ Starting Tobyworld Mirror V3 @ http://$HOST:$PORT  (app=tobyworld.api.server:app)"
exec uvicorn --app-dir "$APP_DIR" tobyworld.api.server:app \
  --host "$HOST" --port "$PORT" \
  --reload --reload-dir "$APP_DIR"
