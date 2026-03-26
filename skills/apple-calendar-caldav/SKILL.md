---
name: apple-calendar-caldav
description: Read and write Apple Calendar / iCloud calendars through CalDAV using environment-provided credentials. Use when a user wants to list available Apple calendars, inspect upcoming events, or create simple events without assuming local macOS Calendar access. Best for setups where credentials live in a local .env file and the skill must remain publishable and free of personal data.
---

# Apple Calendar CalDAV

Use the bundled script to talk to Apple Calendar through CalDAV. Keep credentials out of the skill itself. Read them from environment variables or a local `.env` file.

## Required configuration

Expect these variables to exist in the shell environment or in a local env file passed with `--env-file`:

- `APPLE_CALDAV_URL`
- `APPLE_CALDAV_USERNAME`
- `APPLE_CALDAV_PASSWORD`
- `APPLE_CALDAV_CALENDAR` (optional default calendar)
- `APPLE_CALDAV_MODE` (`readonly` or `readwrite`)

Do not hardcode personal values into the skill.

## Quick workflow

1. Confirm the env file exists and is ignored by git.
2. Use `scripts/caldav_apple.py list-calendars` to discover available calendars.
3. Use `scripts/caldav_apple.py list-events` to inspect upcoming events.
4. Use `scripts/caldav_apple.py create-all-day-event` only when write access is intended and `APPLE_CALDAV_MODE` allows it.

## Commands

Run from the skill directory or with a full path.

### List calendars

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  list-calendars
```

### List future events

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  list-events --days 30 --limit 10
```

If `--calendar` is omitted, the script falls back to `APPLE_CALDAV_CALENDAR`.

### Create an all-day event

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  create-all-day-event --title "nyx" --date 2026-03-27
```

Use `--description` when useful.

## Behavior notes

- Prefer `list-calendars` before assuming a calendar name.
- Treat `VEVENT` calendars as event calendars and `VTODO` calendars as task lists.
- Refuse writes when `APPLE_CALDAV_MODE` is not a write-capable value.
- Keep output concise and user-facing: calendar names, event titles, dates, and creation status.
- Surface failures plainly: missing env vars, auth failure, missing calendar, or write-disabled mode.

## Resource

### scripts/caldav_apple.py

Use this helper for:

- CalDAV discovery
- listing calendars
- listing future events in a date window
- creating all-day events

Prefer extending this script rather than embedding ad-hoc CalDAV XML in future tasks.
