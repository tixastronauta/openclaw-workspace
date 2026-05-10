# Nyx Mission Control

Started: 2026-05-10

A read-only, local-only Mission Control POC for Nyx/OpenClaw. It is meant to give Tiago a global cockpit for what is active, what needs attention, what ran well or badly, and how project work can be resumed without digging through chat history.

## POC scope

- Dark web dashboard, local-only.
- Read-only: no approvals, command execution, cron edits, messages, or project edits.
- Sources: OpenClaw cron CLI when available, workspace `projects/*`, OpenClaw logs, and local activity signals.
- Realtime updates via SSE.
- Small local cache under `data/` for normalized events. The cache is an index, not the source of truth.

## Run locally

```bash
cd /data/.openclaw/workspace/projects/nyx-mission-control
npm start
```

Open: <http://127.0.0.1:4317>

## Docker sidecar

```bash
cd /data/.openclaw/workspace/projects/nyx-mission-control
docker compose up -d --build
```

The POC binds to `127.0.0.1:4317` by default.
