#!/usr/bin/env python3
"""Import monthly credit-card statement PDFs from Gmail into the Drive source folder.

Configuration lives in the Google Sheet tab `Email Import Config`.
The script searches each active Gmail query, downloads the first matching PDF
attachment from the most recent matching email, uploads it to Drive using the
project filename convention, and reports successes/failures.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any

DEFAULT_SPREADSHEET_ID = "1OqVVZPawOU_8bakipfUVSrofmiJeJTiAbkZLtaDE20Y"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
CONFIG_RANGE = "'Email Import Config'!A1:I500"


@dataclass
class Config:
    bank: str
    doc_type: str
    query: str
    attachment_regex: str
    folder_id: str
    name_template: str
    no_pdf_message: str
    notes: str


def run(cmd: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, check=True, text=True, capture_output=True)
    return result.stdout


def gog(args: list[str], account: str, *, cwd: Path | None = None) -> str:
    return run(["gog", *args, "--no-input", "-a", account], cwd=cwd)


def load_values(spreadsheet_id: str, range_a1: str, account: str) -> list[list[str]]:
    raw = gog(["sheets", "get", spreadsheet_id, range_a1, "--json"], account)
    return json.loads(raw).get("values", [])


def load_config(spreadsheet_id: str, account: str) -> list[Config]:
    values = load_values(spreadsheet_id, CONFIG_RANGE, account)
    configs: list[Config] = []
    for row in values[1:]:
        row = (row + [""] * 9)[:9]
        active, bank, doc_type, query, attachment_regex, folder_id, name_template, no_pdf_message, notes = row
        if active.strip().lower() not in {"sim", "s", "yes", "true", "1"}:
            continue
        configs.append(Config(bank=bank.strip(), doc_type=doc_type.strip(), query=query.strip(), attachment_regex=attachment_regex.strip() or r".*\.pdf$", folder_id=folder_id.strip(), name_template=name_template.strip(), no_pdf_message=no_pdf_message.strip(), notes=notes.strip()))
    return configs


def previous_month_yyyymm(today: date | None = None) -> str:
    today = today or date.today()
    year = today.year
    month = today.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year}{month:02d}"


def infer_yyyymm(config: Config, thread: dict[str, Any], attachment: dict[str, Any] | None, fallback_yyyymm: str | None) -> str:
    candidates = []
    if attachment:
        candidates.append(attachment.get("filename", ""))
    candidates.append(thread.get("subject", ""))
    for text in candidates:
        m = re.search(r"(20\d{2})[-_ ]?(0[1-9]|1[0-2])", text or "")
        if m:
            return f"{m.group(1)}{m.group(2)}"
    # Prefer the explicit/import target month when filenames do not contain a
    # useful YYYYMM. Some banks, notably ActivoBank, use generic attachment
    # names like `DOC 202600005` and the email date may be in the next month.
    if fallback_yyyymm:
        return fallback_yyyymm
    return previous_month_yyyymm()


def date_window_query(query: str, yyyymm: str | None) -> str:
    if not yyyymm:
        return query
    year = int(yyyymm[:4])
    month = int(yyyymm[4:6])
    start = date(year, month, 1)
    if month == 12:
        end_year, end_month = year + 1, 1
    else:
        end_year, end_month = year, month + 1
    # Include the first 10 days of the following month because some banks emit
    # the previous month's statement only after month close.
    end = date(end_year, end_month, 10)
    return f"{query} after:{start:%Y/%m/%d} before:{end:%Y/%m/%d}"


def existing_drive_names(folder_id: str, account: str) -> set[str]:
    raw = gog(["drive", "ls", "--parent", folder_id, "--max", "500", "--json"], account)
    return {f["name"] for f in json.loads(raw).get("files", [])}


def process_config(config: Config, account: str, fallback_yyyymm: str | None, dry_run: bool) -> dict[str, Any]:
    effective_query = date_window_query(config.query, fallback_yyyymm)
    search = json.loads(gog(["gmail", "search", effective_query, "--max", "1", "--json"], account))
    threads = search.get("threads", [])
    result: dict[str, Any] = {"bank": config.bank, "query": config.query, "effective_query": effective_query, "status": "failed"}
    if not threads:
        result.update(reason="Nenhum email encontrado para o filtro.")
        return result

    thread = threads[0]
    result.update(thread={k: thread.get(k) for k in ["id", "date", "from", "subject"]})
    attachments = json.loads(gog(["gmail", "thread", "attachments", thread["id"], "--json"], account)).get("attachments", [])
    regex = re.compile(config.attachment_regex, re.I)
    pdfs = [a for a in attachments if regex.search(a.get("filename", "")) and a.get("filename", "").lower().endswith(".pdf")]
    result["attachments"] = [a.get("filename") for a in attachments]

    if not pdfs:
        result.update(status="manual", reason=config.no_pdf_message or "Email encontrado, mas sem PDF importável.")
        return result

    attachment = pdfs[0]
    yyyymm = infer_yyyymm(config, thread, attachment, fallback_yyyymm)
    dest_name = config.name_template.replace("{YYYYMM}", yyyymm)
    result.update(source_attachment=attachment.get("filename"), target_name=dest_name, yyyymm=yyyymm)

    existing = existing_drive_names(config.folder_id, account)
    if dest_name in existing:
        result.update(status="exists", reason="Ficheiro já existe na pasta Drive.")
        return result
    if dry_run:
        result.update(status="dry-run", reason="Dry-run: não descarreguei nem fiz upload.")
        return result

    with tempfile.TemporaryDirectory(prefix="card-email-import-") as tmp:
        local_path = Path(tmp) / dest_name
        gog(["gmail", "attachment", attachment["messageId"], attachment["attachmentId"], "--out", str(local_path), "--name", dest_name], account)
        upload = json.loads(gog(["drive", "upload", str(local_path), "--name", dest_name, "--parent", config.folder_id, "--json"], account))
    result.update(status="imported", drive_file=upload)
    return result


def format_telegram(results: list[dict[str, Any]]) -> str:
    lines = ["Extratos de cartões — importação mensal"]
    for r in results:
        bank = r["bank"]
        status = r["status"]
        if status == "imported":
            lines.append(f"✅ {bank}: importado `{r['target_name']}`")
        elif status == "exists":
            lines.append(f"☑️ {bank}: já existia `{r['target_name']}`")
        elif status == "manual":
            lines.append(f"⚠️ {bank}: {r['reason']}")
        elif status == "dry-run":
            lines.append(f"🧪 {bank}: dry-run `{r['target_name']}`")
        else:
            lines.append(f"❌ {bank}: {r.get('reason', 'falhou')}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID)
    parser.add_argument("--account", default=DEFAULT_ACCOUNT)
    parser.add_argument("--yyyymm", default=previous_month_yyyymm(), help="Fallback/import target month, e.g. 202604. Defaults to previous calendar month.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--summary-out", type=Path)
    args = parser.parse_args()

    configs = load_config(args.spreadsheet_id, args.account)
    results = [process_config(config, args.account, args.yyyymm, args.dry_run) for config in configs]
    summary = {"results": results, "telegram_message": format_telegram(results)}
    text = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.summary_out:
        args.summary_out.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
