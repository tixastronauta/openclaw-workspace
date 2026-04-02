# OpenClaw Workspace

This repo contains the versioned `workspace/` for my OpenClaw assistant setup.

## What lives here

- assistant behavior and operating rules (`AGENTS.md`, `SOUL.md`)
- user context (`USER.md`)
- assistant identity (`IDENTITY.md`)
- local setup notes (`TOOLS.md`)
- long-term memory (`MEMORY.md`)
- daily notes and short-term continuity (`memory/`)

## What this repo is for

This is the durable, human-readable part of the setup.
It is meant to be safe to version, review, and restore.

## What should not live here

Do not intentionally store secrets in this repo.
Examples:
- API keys
- bot tokens
- session cookies
- private credentials copied from `~/.openclaw/credentials/`

Runtime state, credentials, logs, and channel auth belong outside this repo.

## Git policy

Meaningful completed changes in this workspace may be automatically committed and pushed to the configured private remote.
The goal is useful history, not noisy history.
