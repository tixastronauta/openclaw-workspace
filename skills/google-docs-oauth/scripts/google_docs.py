#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _dependency_error(exc: Exception) -> None:
    print(
        json.dumps(
            {
                "ok": False,
                "error": "missing_dependency",
                "message": (
                    "Missing Google API dependency. Install: "
                    "python3 -m pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
                ),
                "details": str(exc),
            },
            indent=2,
        ),
        file=sys.stderr,
    )
    raise SystemExit(2)


try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except Exception as exc:  # pragma: no cover
    _dependency_error(exc)


DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/documents",
]
DOC_ID_RE = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")


def parse_doc_id(value: str) -> str:
    value = value.strip()
    match = DOC_ID_RE.search(value)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", value):
        return value
    raise ValueError(f"Could not extract a Google Doc ID from: {value}")



def load_env_file(path: Optional[str]) -> None:
    if not path:
        return
    env_path = Path(path).expanduser()
    if not env_path.exists():
        raise FileNotFoundError(f"Env file not found: {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)



def env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value or ""



def resolve_scopes() -> List[str]:
    raw = os.getenv("GOOGLE_DOCS_SCOPES", "").strip()
    if not raw:
        return list(DEFAULT_SCOPES)
    return [item.strip() for item in raw.split(",") if item.strip()]



def get_credentials() -> Credentials:
    client_secret_file = Path(env("GOOGLE_DOCS_CLIENT_SECRET_FILE", required=True)).expanduser()
    token_file = Path(env("GOOGLE_DOCS_TOKEN_FILE", required=True)).expanduser()
    token_file.parent.mkdir(parents=True, exist_ok=True)
    scopes = resolve_scopes()

    creds = None
    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), scopes)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json(), encoding="utf-8")
        return creds

    if not client_secret_file.exists():
        raise FileNotFoundError(f"OAuth client secret file not found: {client_secret_file}")

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), scopes)
    open_browser = env("GOOGLE_DOCS_OPEN_BROWSER", "true").lower() not in {"0", "false", "no"}
    creds = flow.run_local_server(port=0, open_browser=open_browser)
    token_file.write_text(creds.to_json(), encoding="utf-8")
    return creds



def docs_service():
    return build("docs", "v1", credentials=get_credentials(), cache_discovery=False)



def document_text(document: Dict[str, Any]) -> str:
    parts: List[str] = []
    for el in document.get("body", {}).get("content", []):
        para = el.get("paragraph")
        if not para:
            continue
        for pe in para.get("elements", []):
            text_run = pe.get("textRun")
            if text_run:
                parts.append(text_run.get("content", ""))
    return "".join(parts)



def end_index(document: Dict[str, Any]) -> int:
    content = document.get("body", {}).get("content", [])
    if not content:
        return 1
    return int(content[-1].get("endIndex", 1))



def replace_all_requests(document: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
    end = end_index(document)
    requests: List[Dict[str, Any]] = []
    if end > 2:
        requests.append({"deleteContentRange": {"range": {"startIndex": 1, "endIndex": end - 1}}})
    if text:
        requests.append({"insertText": {"location": {"index": 1}, "text": text}})
    return requests



def append_text_requests(document: Dict[str, Any], text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    idx = max(1, end_index(document) - 1)
    return [{"insertText": {"location": {"index": idx}, "text": text}}]



def insert_text_requests(index: int, text: str) -> List[Dict[str, Any]]:
    if index < 1:
        raise ValueError("Insertion index must be >= 1")
    if not text:
        return []
    return [{"insertText": {"location": {"index": index}, "text": text}}]



def load_requests_arg(raw: Optional[str], requests_file: Optional[str]) -> List[Dict[str, Any]]:
    if raw and requests_file:
        raise ValueError("Use either --requests-json or --requests-file, not both")
    if raw:
        return json.loads(raw)
    if requests_file:
        return json.loads(Path(requests_file).expanduser().read_text(encoding="utf-8"))
    return []



def cmd_get(args: argparse.Namespace) -> Dict[str, Any]:
    svc = docs_service()
    doc_id = parse_doc_id(args.doc)
    doc = svc.documents().get(documentId=doc_id).execute()
    payload: Dict[str, Any] = {
        "ok": True,
        "documentId": doc_id,
        "title": doc.get("title", ""),
    }
    if args.include_json:
        payload["document"] = doc
    else:
        payload["text"] = document_text(doc)
    return payload



def run_batch_update(doc_id: str, requests: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not requests:
        return {"ok": True, "documentId": doc_id, "applied": 0, "replies": []}
    svc = docs_service()
    result = svc.documents().batchUpdate(documentId=doc_id, body={"requests": requests}).execute()
    return {
        "ok": True,
        "documentId": doc_id,
        "applied": len(requests),
        "replies": result.get("replies", []),
        "writeControl": result.get("writeControl", {}),
    }



def cmd_append(args: argparse.Namespace) -> Dict[str, Any]:
    svc = docs_service()
    doc_id = parse_doc_id(args.doc)
    doc = svc.documents().get(documentId=doc_id).execute()
    return run_batch_update(doc_id, append_text_requests(doc, args.text))



def cmd_replace(args: argparse.Namespace) -> Dict[str, Any]:
    svc = docs_service()
    doc_id = parse_doc_id(args.doc)
    doc = svc.documents().get(documentId=doc_id).execute()
    return run_batch_update(doc_id, replace_all_requests(doc, args.text))



def cmd_insert(args: argparse.Namespace) -> Dict[str, Any]:
    doc_id = parse_doc_id(args.doc)
    return run_batch_update(doc_id, insert_text_requests(args.index, args.text))



def cmd_batch_update(args: argparse.Namespace) -> Dict[str, Any]:
    doc_id = parse_doc_id(args.doc)
    requests = load_requests_arg(args.requests_json, args.requests_file)
    return run_batch_update(doc_id, requests)



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read and edit Google Docs through OAuth.")
    parser.add_argument("--env-file", help="Optional .env file to load before reading environment variables")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")

    sub = parser.add_subparsers(dest="command", required=True)

    p_get = sub.add_parser("get", help="Fetch a document as plain text or raw JSON")
    p_get.add_argument("--doc", required=True, help="Google Doc ID or URL")
    p_get.add_argument("--include-json", action="store_true", help="Include the raw document JSON instead of plain text")
    p_get.set_defaults(func=cmd_get)

    p_append = sub.add_parser("append", help="Append text to the end of a document")
    p_append.add_argument("--doc", required=True, help="Google Doc ID or URL")
    p_append.add_argument("--text", required=True, help="Text to append")
    p_append.set_defaults(func=cmd_append)

    p_replace = sub.add_parser("replace-all", help="Replace the full document body with new text")
    p_replace.add_argument("--doc", required=True, help="Google Doc ID or URL")
    p_replace.add_argument("--text", required=True, help="Replacement text")
    p_replace.set_defaults(func=cmd_replace)

    p_insert = sub.add_parser("insert", help="Insert text at a specific Google Docs character index")
    p_insert.add_argument("--doc", required=True, help="Google Doc ID or URL")
    p_insert.add_argument("--index", type=int, required=True, help="Google Docs location index")
    p_insert.add_argument("--text", required=True, help="Text to insert")
    p_insert.set_defaults(func=cmd_insert)

    p_batch = sub.add_parser("batch-update", help="Run raw Google Docs batchUpdate requests")
    p_batch.add_argument("--doc", required=True, help="Google Doc ID or URL")
    p_batch.add_argument("--requests-json", help="Inline JSON array of batchUpdate requests")
    p_batch.add_argument("--requests-file", help="Path to a JSON file containing a requests array")
    p_batch.set_defaults(func=cmd_batch_update)

    return parser



def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    load_env_file(args.env_file)
    try:
        result = args.func(args)
    except Exception as exc:
        payload = {"ok": False, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(payload, indent=2), file=sys.stderr)
        raise SystemExit(1)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.command == "get" and "text" in result:
        print(result["text"])
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
