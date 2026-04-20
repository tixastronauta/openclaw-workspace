---
name: startup-ping
description: "Send a Telegram resurrection ping on gateway startup"
metadata:
  { "openclaw": { "emoji": "😼", "events": ["gateway:startup"] } }
---

# Startup Ping

Sends a deterministic Telegram message on gateway startup without relying on LLM tool availability.
