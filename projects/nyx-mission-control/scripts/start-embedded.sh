#!/usr/bin/env sh
set -eu

APP_DIR="${NYX_MC_APP_DIR:-/data/.openclaw/workspace/projects/nyx-mission-control}"
PORT="${NYX_MC_PORT:-4317}"
HOST="${NYX_MC_HOST:-0.0.0.0}"
WORKSPACE_DIR="${WORKSPACE_DIR:-/data/.openclaw/workspace}"
OPENCLAW_DIR="${OPENCLAW_DIR:-/data/.openclaw}"
CACHE_DIR="${CACHE_DIR:-$APP_DIR/data}"
REFRESH_MS="${REFRESH_MS:-30000}"
PID_FILE="$CACHE_DIR/mission-control.pid"
LOG_FILE="$CACHE_DIR/mission-control.log"

mkdir -p "$CACHE_DIR"

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "Nyx Mission Control already running with pid $PID"
    exit 0
  fi
fi

cd "$APP_DIR"

HOST="$HOST" \
PORT="$PORT" \
WORKSPACE_DIR="$WORKSPACE_DIR" \
OPENCLAW_DIR="$OPENCLAW_DIR" \
CACHE_DIR="$CACHE_DIR" \
REFRESH_MS="$REFRESH_MS" \
nohup npm start >> "$LOG_FILE" 2>&1 &

PID="$!"
echo "$PID" > "$PID_FILE"
echo "Nyx Mission Control started on http://$HOST:$PORT with pid $PID"
echo "Logs: $LOG_FILE"
