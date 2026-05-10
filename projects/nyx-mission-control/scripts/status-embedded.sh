#!/usr/bin/env sh
set -eu

APP_DIR="${NYX_MC_APP_DIR:-/data/.openclaw/workspace/projects/nyx-mission-control}"
PORT="${NYX_MC_PORT:-4317}"
HOST="${NYX_MC_HOST:-127.0.0.1}"
CACHE_DIR="${CACHE_DIR:-$APP_DIR/data}"
PID_FILE="$CACHE_DIR/mission-control.pid"

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "process: running pid $PID"
  else
    echo "process: stale pid file ($PID)"
  fi
else
  echo "process: no pid file"
fi

node -e "const http=require('http');const req=http.get({host:'$HOST',port:$PORT,path:'/healthz',timeout:2000},res=>{let b='';res.on('data',d=>b+=d);res.on('end',()=>{console.log('health:',res.statusCode,b)})});req.on('error',e=>{console.log('health: error',e.message);process.exitCode=1});req.on('timeout',()=>{req.destroy(new Error('timeout'))})"
