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

If the Projects page is empty, the sidecar is probably not seeing the host workspace path. Set the host paths explicitly before starting:

```bash
cat > .env <<'EOF'
WORKSPACE_HOST_DIR=/actual/host/path/to/.openclaw/workspace
OPENCLAW_HOST_DIR=/actual/host/path/to/.openclaw
EOF

docker compose up -d --build
```

Inside the container, `WORKSPACE_DIR` remains `/workspace`; the `.env` variables only control the host-side bind mounts.

## Cron collector note

The Crons page uses the `openclaw cron list` CLI. The default sidecar base image is `node:24-alpine`, which does not include the OpenClaw CLI, so the Crons page will show the cron source as unavailable.

If you have a custom OpenClaw image that includes Node and the `openclaw` CLI, build with it:

```bash
cat >> .env <<'EOF'
NYX_MC_BASE_IMAGE=your-openclaw-image:tag
EOF

docker compose up -d --build
```

Quick check:

```bash
docker exec nyx-mission-control which openclaw
docker exec nyx-mission-control openclaw cron list
```
