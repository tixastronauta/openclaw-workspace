---
name: nyx-mission-control-startup
description: "Start Nyx Mission Control when the Gateway starts"
metadata:
  { "openclaw": { "emoji": "🛰️", "events": ["gateway:startup"], "requires": { "bins": ["node", "npm", "sh"] } } }
---

# Nyx Mission Control Startup

Starts the embedded Nyx Mission Control web dashboard on `gateway:startup`.

The hook is intentionally small and delegates idempotency/logging to:

`/data/.openclaw/workspace/projects/nyx-mission-control/scripts/start-embedded.sh`
