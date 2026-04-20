---
name: imap-smtp-email-safe
description: Read, search, summarize, send, and reply to email via IMAP/SMTP using credentials stored in a local workspace secrets .env file. Use when the user wants mailbox access for triage, fetching recent messages, reading full emails, drafting or sending replies, checking SMTP/IMAP connectivity, or handling a small number of email operations directly from OpenClaw without a heavyweight mail client.
---

# IMAP/SMTP Email Safe

Use this skill for direct mailbox work through IMAP and SMTP.

This skill is intentionally small and predictable:
- prefer `workspace/secrets/.env` for credentials
- use Python standard-library IMAP/SMTP operations
- support read-first workflows by default
- only send/reply when explicitly asked

## Credentials and config

Read credentials from:
- `/data/.openclaw/workspace/secrets/.env`

Expected keys:

```env
IMAP_HOST=imap.example.com
IMAP_PORT=993
IMAP_SECURE=true
IMAP_USER=user@example.com
IMAP_PASS=app-password-or-password
IMAP_MAILBOX=INBOX

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_SECURE=false
SMTP_USER=user@example.com
SMTP_PASS=app-password-or-password
SMTP_FROM=user@example.com
```

Notes:
- `IMAP_MAILBOX` is optional and defaults to `INBOX`
- `SMTP_HOST` and `SMTP_PORT` are required for sending/replying
- `SMTP_USER`/`SMTP_PASS` fall back to `IMAP_USER`/`IMAP_PASS` if omitted
- `SMTP_FROM` falls back to `SMTP_USER`, then `IMAP_USER`
- prefer app passwords when the provider supports them

## Default workflow

### Read / triage

Use the bundled script:

```bash
python3 scripts/email_client.py list-mailboxes
python3 scripts/email_client.py recent --limit 10
python3 scripts/email_client.py read --uid <uid>
python3 scripts/email_client.py search --from foo@example.com
```

Default behavior:
- read-only unless the user explicitly asks to send/reply
- list headers before full bodies when possible
- do not mark messages read unless requested

### Send / reply

Only send when the user explicitly asks.

Examples:

```bash
python3 scripts/email_client.py send --to person@example.com --subject "Hello" --body "World"
python3 scripts/email_client.py reply --uid 123 --body "Sounds good"
```

For replies:
- fetch the original message first
- preserve sensible thread headers when available (`In-Reply-To`, `References`)
- generate `Re:` only if needed
- default reply recipient is the original `Reply-To` or `From`

## Commands

### `list-mailboxes`
List available folders.

### `recent`
Show recent message headers from the configured mailbox.

Options:
- `--limit <n>` default `10`
- `--mailbox <name>` override mailbox

### `read`
Read one message by UID.

Options:
- `--uid <uid>` required
- `--mailbox <name>` override mailbox

### `search`
Search message headers.

Options:
- `--from <text>`
- `--subject <text>`
- `--since <YYYY-MM-DD>`
- `--unseen`
- `--limit <n>` default `20`
- `--mailbox <name>` override mailbox

### `send`
Send a new email.

Options:
- `--to <email>` required
- `--subject <text>` required
- `--body <text>` required
- `--cc <emails>` optional
- `--bcc <emails>` optional

### `reply`
Reply to an existing email by UID.

Options:
- `--uid <uid>` required
- `--body <text>` required
- `--mailbox <name>` override mailbox
- `--reply-all` optional

### `smtp-test`
Verify SMTP connectivity without sending a normal user message.

## Safety rules

- Do not send or reply unless the user explicitly asked for it
- Prefer reading headers first, then full body
- Avoid bulk operations; this skill is for small, deliberate mailbox actions
- If SMTP settings are missing, say so clearly instead of guessing
- If authentication fails, report the exact failure briefly
