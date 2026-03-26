---
name: apple-calendar-caldav
description: Read and write Apple Calendar / iCloud calendars through CalDAV using environment-provided credentials. Use when a user wants to list available Apple calendars, inspect upcoming events, search events by text, create events with date or time, update existing events, delete events, handle recurring events, or consume machine-friendly JSON output without assuming local macOS Calendar access. Best for setups where credentials live in a local .env file and the skill must remain publishable and free of personal data.
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
- `APPLE_CALDAV_TIMEZONE` (optional IANA timezone such as `Europe/Lisbon`; defaults to `UTC`)

Do not hardcode personal values into the skill.

## Quick workflow

1. Confirm the env file exists and is ignored by git.
2. Use `scripts/caldav_apple.py list-calendars --json` to discover available calendars.
3. Use `scripts/caldav_apple.py list-events --json` or `find-events --json` to inspect events and capture `uid`/`href`.
4. Use `create-event` for timed or all-day events.
5. Use `update-event` or `delete-event` with `uid` or `href` for changes.
6. For recurring events, use `--rrule` when creating or updating, and use `--recurrence-id` when targeting a specific recurring instance.

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

By default, recurring events are expanded into visible instances inside the requested window. Use `--no-expand` to inspect base events instead.

### Search events by text

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --json \
  find-events --query "dentista" --lookback-days 30 --days 365 --limit 20
```

### Create a timed event with timezone-aware naive input

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --timezone Europe/Lisbon \
  --json \
  create-event \
  --title "Reunião Nyx" \
  --start 2026-03-27T14:00:00 \
  --end 2026-03-27T15:00:00 \
  --description "teste" \
  --location "online"
```

When the datetime has no offset, the script interprets it using `--timezone` or `APPLE_CALDAV_TIMEZONE`.

### Create an all-day event

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --json \
  create-event --title "nyx" --start 2026-03-27 --end 2026-03-28
```

### Create a recurring event

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --timezone Europe/Lisbon \
  --json \
  create-event \
  --title "Standup" \
  --start 2026-03-30T09:00:00 \
  --end 2026-03-30T09:15:00 \
  --rrule "FREQ=WEEKLY;COUNT=5"
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

### Update recurrence rule or target a specific recurring instance

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --json \
  update-event \
  --uid EVENT_UID \
  --rrule "FREQ=WEEKLY;COUNT=8"
```

```bash
python3 scripts/caldav_apple.py \
  --env-file /path/to/.env \
  --calendar "Pessoal" \
  --json \
  update-event \
  --uid EVENT_UID \
  --recurrence-id 20260330T080000Z \
  --title "Standup movido"
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
- Naive datetimes are interpreted with `--timezone` or `APPLE_CALDAV_TIMEZONE`.
- JSON output includes both UTC and local/timezone-aware values where available.
- `list-events` expands recurring events by default so searches and listings show actual instances in the chosen window.
- Use `--no-expand` when you need the base recurring object rather than expanded instances.
- Surface failures plainly: missing env vars, auth failure, missing calendar, write-disabled mode, invalid timezone, or missing event identifier.

## Resource

### scripts/caldav_apple.py

Use this helper for:

- CalDAV discovery
- listing calendars
- listing future events
- searching events by text
- creating all-day or timed events
- handling timezone-aware and naive datetimes
- creating and updating recurring events via RRULE
- updating events
- deleting events
- machine-friendly JSON output

Prefer extending this script rather than embedding ad-hoc CalDAV XML in future tasks.
