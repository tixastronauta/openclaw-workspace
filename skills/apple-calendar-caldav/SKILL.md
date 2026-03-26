---
name: apple-calendar-caldav
description: Read and write Apple Calendar / iCloud calendars through CalDAV using environment-provided credentials. Use when a user wants to list available Apple calendars, inspect upcoming events, create events with date or time, update existing events, delete events, or consume machine-friendly JSON output without assuming local macOS Calendar access. Best for setups where credentials live in a local .env file and the skill must remain publishable and free of personal data.
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
2. Use `scripts/caldav_apple.py list-calendars --json` to discover available calendars.
3. Use `scripts/caldav_apple.py list-events --json` to inspect upcoming events and capture `uid`/`href`.
4. Use `create-event` for timed or all-day events.
5. Use `update-event` or `delete-event` with `uid` or `href` for changes.

## Commands

Run from the skill directory or with a full path.

### List calendars

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --json \
  list-calendars
```

### List future events

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --json \
  list-events --days 30 --limit 10
```

If `--calendar` is omitted, the script falls back to `APPLE_CALDAV_CALENDAR`.

### Create a timed event

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --json \
  create-event \
  --title "Reunião Nyx" \
  --start 2026-03-27T14:00:00Z \
  --end 2026-03-27T15:00:00Z \
  --description "teste" \
  --location "online"
```

### Create an all-day event

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --json \
  create-event --title "nyx" --start 2026-03-27 --end 2026-03-28
```

### Update an event

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --json \
  update-event \
  --uid EVENT_UID \
  --title "Novo título" \
  --start 2026-03-27T15:00:00Z \
  --end 2026-03-27T16:00:00Z
```

### Delete an event

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --json \
  delete-event --uid EVENT_UID
```

## Behavior notes

- Prefer JSON output for automation.
- Prefer `list-calendars` before assuming a calendar name.
- Use `uid` or `href` from `list-events --json` to target updates and deletes.
- Refuse writes when `APPLE_CALDAV_MODE` is not a write-capable value.
- Timed events use UTC when an explicit timezone is not provided.
- Surface failures plainly: missing env vars, auth failure, missing calendar, write-disabled mode, or missing event identifier.

## Resource

### scripts/caldav_apple.py

Use this helper for:

- CalDAV discovery
- listing calendars
- listing future events
- creating all-day or timed events
- updating events
- deleting events
- machine-friendly JSON output

Prefer extending this script rather than embedding ad-hoc CalDAV XML in future tasks.
