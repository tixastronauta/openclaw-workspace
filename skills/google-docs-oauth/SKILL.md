---
name: google-docs-oauth
description: Read and edit Google Docs through the Google Docs API using OAuth credentials supplied via environment variables or a local .env file. Use when a user wants to inspect a Google Doc, append text, replace the full document body, insert text at a specific location, or run raw batchUpdate edits against an existing Google Doc without hardcoded secrets or personal data in the skill.
---

# Google Docs OAuth

Use the bundled script to work with existing Google Docs through OAuth. Keep credentials and token files outside the skill itself. Read them from environment variables or from a local `.env` file passed with `--env-file`.

## Required configuration

Expect these variables to exist in the shell environment or in a local env file:

- `GOOGLE_DOCS_CLIENT_SECRET_FILE` — path to the OAuth client credentials JSON downloaded from Google Cloud
- `GOOGLE_DOCS_TOKEN_FILE` — path where the OAuth access/refresh token JSON should be stored
- `GOOGLE_DOCS_SCOPES` — optional comma-separated scopes; defaults to `https://www.googleapis.com/auth/documents`
- `GOOGLE_DOCS_OPEN_BROWSER` — optional; `true` by default. Set to `false` if the OAuth flow should avoid opening a browser automatically

Do not hardcode personal values into the skill.

## Dependency requirement

The helper script requires these Python packages:

```bash
python3 -m pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

## Quick workflow

1. Confirm the OAuth client credentials JSON exists outside the skill directory.
2. Store local paths in a `.env` file that is ignored by git.
3. Use `get` to read the current document text before making non-trivial edits.
4. Use `append` for additive changes.
5. Use `replace-all` when the user wants the full body rewritten.
6. Use `insert` when the edit position is known by Google Docs index.
7. Use `batch-update` for richer edits driven by raw Google Docs API requests.

## Suggested local `.env`

```dotenv
GOOGLE_DOCS_CLIENT_SECRET_FILE=/absolute/path/to/google-client-secret.json
GOOGLE_DOCS_TOKEN_FILE=/absolute/path/to/google-docs-token.json
GOOGLE_DOCS_SCOPES=https://www.googleapis.com/auth/documents
GOOGLE_DOCS_OPEN_BROWSER=true
```

Keep this file local and out of version control.

## Commands

Run from the skill directory or with a full path.

### Read a document as plain text

```bash
python3 scripts/google_docs.py \
  --env-file /path/to/.env \
  get \
  --doc "https://docs.google.com/document/d/DOCUMENT_ID/edit"
```

### Read a document and return raw Google Docs JSON

```bash
python3 scripts/google_docs.py \
  --env-file /path/to/.env \
  --json \
  get \
  --doc DOCUMENT_ID \
  --include-json
```

### Append text

```bash
python3 scripts/google_docs.py \
  --env-file /path/to/.env \
  --json \
  append \
  --doc DOCUMENT_ID \
  --text "\n\nNew paragraph added by Nyx."
```

### Replace the full document body

```bash
python3 scripts/google_docs.py \
  --env-file /path/to/.env \
  --json \
  replace-all \
  --doc DOCUMENT_ID \
  --text "Full replacement body"
```

### Insert text at a specific Google Docs index

```bash
python3 scripts/google_docs.py \
  --env-file /path/to/.env \
  --json \
  insert \
  --doc DOCUMENT_ID \
  --index 57 \
  --text "inserted text"
```

### Run raw batchUpdate requests

```bash
python3 scripts/google_docs.py \
  --env-file /path/to/.env \
  --json \
  batch-update \
  --doc DOCUMENT_ID \
  --requests-json '[
    {
      "insertText": {
        "location": {"index": 1},
        "text": "Hello from the Google Docs API\n"
      }
    }
  ]'
```

Or load requests from a file:

```bash
python3 scripts/google_docs.py \
  --env-file /path/to/.env \
  --json \
  batch-update \
  --doc DOCUMENT_ID \
  --requests-file /path/to/requests.json
```

## Behavior notes

- Accept either a raw document ID or a standard Google Docs URL in `--doc`.
- On first use, the script runs a local OAuth flow and writes the token to `GOOGLE_DOCS_TOKEN_FILE`.
- `get` returns plain text by default; use `--include-json` for the raw API document payload.
- `replace-all` rewrites the document body content. It is intentionally blunt.
- `insert` works with Google Docs character indices, not line numbers.
- `batch-update` is the escape hatch for complex formatting or structural edits.
- Surface failures plainly: missing env vars, missing credentials file, OAuth/token issues, invalid doc ID, missing dependencies, or malformed request JSON.

## Resource

### scripts/google_docs.py

Use this helper for:

- OAuth login and token refresh
- reading existing Google Docs
- appending text
- replacing all document text
- inserting text at a known index
- sending raw `documents.batchUpdate` requests for richer edits

Prefer extending this script rather than hardcoding ad-hoc Google Docs API calls into future tasks.
