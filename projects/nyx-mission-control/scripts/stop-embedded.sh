#!/usr/bin/env sh
set -eu

APP_DIR="${NYX_MC_APP_DIR:-/data/.openclaw/workspace/projects/nyx-mission-control}"
CACHE_DIR="${CACHE_DIR:-$APP_DIR/data}"
PID_FILE="$CACHE_DIR/mission-control.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "Nyx Mission Control is not running: no pid file"
  exit 0
fi

PID="$(cat "$PID_FILE" 2>/dev/null || true)"
if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  echo "Stopped Nyx Mission Control pid $PID"
else
  echo "Nyx Mission Control pid $PID is not running"
fi
rm -f "$PID_FILE"
