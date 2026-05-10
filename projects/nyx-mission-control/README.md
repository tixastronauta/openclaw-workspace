# Nyx Mission Control

Started: 2026-05-10

A read-only, local-only Mission Control POC for Nyx/OpenClaw. It gives Tiago a global cockpit for what is active, what needs attention, what ran well or badly, and how project work can be resumed without digging through chat history.

## Architecture decision

Primary mode is **embedded in the same container/environment where the OpenClaw Gateway runs**.

That environment already has the real OpenClaw CLI, workspace, logs, cron scheduler access, and runtime paths. Running Mission Control there avoids fragile sidecar bind mounts and missing CLI/tooling.

Docker sidecar remains only as a development/fallback option.

## POC scope

- Dark web dashboard, local-only.
- Read-only: no approvals, command execution, cron edits, messages, or project edits.
- Sources: `openclaw cron list --json`, workspace `projects/*`, OpenClaw logs, and local activity signals.
- Calendar-style Scheduled Tasks view inspired by the Mission Control video: weekly cron map plus always-running interval routines.
- Realtime updates via SSE.
- Small local cache under `data/` for normalized events. The cache is an index, not the source of truth.

## Embedded run

Inside the same container/environment where the OpenClaw Gateway runs:

```bash
cd /data/.openclaw/workspace/projects/nyx-mission-control
npm start
```

Open: <http://127.0.0.1:4317>

Useful environment variables:

```bash
NYX_MC_HOST=0.0.0.0
NYX_MC_PORT=4317
WORKSPACE_DIR=/data/.openclaw/workspace
OPENCLAW_DIR=/data/.openclaw
CACHE_DIR=/data/.openclaw/workspace/projects/nyx-mission-control/data
REFRESH_MS=30000
```

## Embedded background service

For the custom OpenClaw image/entrypoint, start Mission Control as a separate background process:

```bash
/data/.openclaw/workspace/projects/nyx-mission-control/scripts/start-embedded.sh
```

Status and stop:

```bash
/data/.openclaw/workspace/projects/nyx-mission-control/scripts/status-embedded.sh
/data/.openclaw/workspace/projects/nyx-mission-control/scripts/stop-embedded.sh
```

Entrypoint/supervisor integration example:

```sh
# Start OpenClaw/Gateway however the image already does it, then also start:
/data/.openclaw/workspace/projects/nyx-mission-control/scripts/start-embedded.sh
```

The script writes:

- PID: `data/mission-control.pid`
- logs: `data/mission-control.log`

## Health and diagnostics

```bash
curl http://127.0.0.1:4317/healthz
curl http://127.0.0.1:4317/api/snapshot
curl http://127.0.0.1:4317/api/diagnostic
```

## Expected runtime checks

These should work in the embedded environment:

```bash
which openclaw
openclaw cron list | head
ls -la /data/.openclaw/workspace/projects
ls -la /data/.openclaw/logs
node -v
npm -v
```

## Docker sidecar fallback / dev only

```bash
cd /data/.openclaw/workspace/projects/nyx-mission-control
docker compose up -d --build
```

If using the sidecar mode, configure host bind mounts in `.env`:

```bash
WORKSPACE_HOST_DIR=/actual/host/path/to/.openclaw/workspace
OPENCLAW_HOST_DIR=/actual/host/path/to/.openclaw
NYX_MC_BASE_IMAGE=your-openclaw-image:tag
```

Sidecar mode is not the recommended production path for this project.
