#!/usr/bin/env python3
"""Backfill `nota_ult_col_json` with DGES last-admitted scores from 2020 onward.

The existing six legacy columns remain untouched. This script only updates:
- `nota_ult_col_json`
- `updated_at`

Source for 2020-2022 (and optionally later years) is the official DGES statistical PDF pattern:
- 1st phase: https://www.dges.gov.pt/guias/pdfs/statce/colYYf1/ecYY_<institution><course>.pdf
- 2nd phase: https://www.dges.gov.pt/guias/pdfs/statce/colYYf2/ecYYf2_<institution><course>.pdf

The script is designed to be polite: process small batches, randomize delays, and skip rows that already
have the requested years populated unless --force is used.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
TAB = "dges_cursos_2026"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
LOG_PATH = Path("projects/dges/data/backfill_entry_scores_from_2020.log")
PROGRESS_PATH = Path("projects/dges/data/backfill_entry_scores_from_2020_progress.json")
YEARS_DEFAULT = [2020, 2021, 2022]


def ensure_dirs() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def now_lisbon() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")


def log(msg: str) -> None:
    line = f"[{now_lisbon()}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def save_progress(payload: dict) -> None:
    PROGRESS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sh(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def gog_base(account: str) -> list[str]:
    return ["gog", "sheets", "--account", account]


def get_sheet(account: str) -> list[list[str]]:
    return json.loads(
        sh(gog_base(account) + ["get", SHEET_ID, f"{TAB}!A1:ZZ2000", "--json", "--no-input"])
    )["values"]


def update_range(account: str, a1_range: str, values: list[list[str]]) -> None:
    subprocess.run(
        gog_base(account)
        + [
            "update",
            SHEET_ID,
            a1_range,
            "--values-json",
            json.dumps(values, ensure_ascii=False),
            "--input",
            "USER_ENTERED",
            "--no-input",
        ],
        check=True,
    )


def column_letter(index_1_based: int) -> str:
    result = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def pdf_url(institution_code: str, course_code: str, year: int, phase: str) -> str:
    yy = str(year)[-2:]
    if phase == "1a":
        return f"https://www.dges.gov.pt/guias/pdfs/statce/col{yy}f1/ec{yy}_{institution_code}{course_code}.pdf"
    if phase == "2a":
        return f"https://www.dges.gov.pt/guias/pdfs/statce/col{yy}f2/ec{yy}f2_{institution_code}{course_code}.pdf"
    raise ValueError(f"unexpected phase: {phase}")


def fetch_pdf_text(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Nyx DGES backfill/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        out = subprocess.check_output(["pdftotext", "-layout", tmp.name, "-"], text=True)
    return out


def parse_general_last_score(pdf_text: str) -> str:
    for line in pdf_text.splitlines():
        if "17 Geral" in line:
            matches = re.findall(r"\b([0-9]{3}[\.,][0-9])\b", line)
            if matches:
                return matches[-1].replace(",", ".")
    return ""


def parse_years(institution_code: str, course_code: str, years: list[int], request_gap_low: float, request_gap_high: float) -> dict[str, dict[str, str]]:
    result = {}
    total_requests = 0
    for year in years:
        result[str(year)] = {}
        for phase in ["1a", "2a"]:
            url = pdf_url(institution_code, course_code, year, phase)
            text = fetch_pdf_text(url)
            result[str(year)][phase] = parse_general_last_score(text) if text else ""
            total_requests += 1
            if total_requests < len(years) * 2:
                time.sleep(random.uniform(request_gap_low, request_gap_high))
    return result


def needs_backfill(obj: dict, years: list[int]) -> bool:
    for year in years:
        y = str(year)
        if y not in obj:
            return True
        if not isinstance(obj[y], dict):
            return True
        if "1a" not in obj[y] or "2a" not in obj[y]:
            return True
    return False


def merge_scores(existing: dict, new_scores: dict[str, dict[str, str]]) -> dict:
    merged = json.loads(json.dumps(existing))
    for year, phases in new_scores.items():
        merged.setdefault(year, {})
        for phase, value in phases.items():
            merged[year][phase] = value
    return merged


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=os.environ.get("GOG_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--institution-sigla")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--years", default="2020,2021,2022")
    parser.add_argument("--request-gap-low", type=float, default=2.0)
    parser.add_argument("--request-gap-high", type=float, default=4.5)
    parser.add_argument("--row-gap-low", type=float, default=6.0)
    parser.add_argument("--row-gap-high", type=float, default=12.0)
    args = parser.parse_args()

    ensure_dirs()
    years = [int(x) for x in args.years.split(",") if x.strip()]
    values = get_sheet(args.account)
    headers = values[0]
    idx = {header: i for i, header in enumerate(headers)}
    required = ["updated_at", "institution_code", "institution_sigla", "course_code", "course_name", "nota_ult_col_json"]
    missing = [name for name in required if name not in idx]
    if missing:
        raise SystemExit(f"Missing required columns: {', '.join(missing)}")

    note_col = column_letter(idx["nota_ult_col_json"] + 1)
    updated_col = column_letter(idx["updated_at"] + 1)

    candidates = []
    for sheet_row, row in enumerate(values[1:], start=2):
        sigla = row[idx["institution_sigla"]] if len(row) > idx["institution_sigla"] else ""
        if args.institution_sigla and sigla != args.institution_sigla:
            continue
        raw = row[idx["nota_ult_col_json"]] if len(row) > idx["nota_ult_col_json"] else ""
        try:
            existing = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            existing = {}
        if args.force or needs_backfill(existing, years):
            candidates.append((sheet_row, row, existing))

    if args.limit:
        candidates = candidates[: args.limit]

    log(f"candidate rows: {len(candidates)}")
    save_progress({"status": "starting", "candidates": len(candidates), "updated": 0, "errors": 0, "dryRun": args.dry_run})

    updated = 0
    errors = 0
    for n, (sheet_row, row, existing) in enumerate(candidates, start=1):
        course_code = row[idx["course_code"]] if len(row) > idx["course_code"] else ""
        institution_code = row[idx["institution_code"]] if len(row) > idx["institution_code"] else ""
        course_name = row[idx["course_name"]] if len(row) > idx["course_name"] else ""
        log(f"[{n}/{len(candidates)}] row {sheet_row} :: {institution_code}/{course_code} :: {course_name}")
        try:
            new_scores = parse_years(institution_code, course_code, years, args.request_gap_low, args.request_gap_high)
            merged = merge_scores(existing, new_scores)
            now = now_lisbon()
            if not args.dry_run:
                update_range(args.account, f"{TAB}!{note_col}{sheet_row}:{note_col}{sheet_row}", [[json.dumps(merged, ensure_ascii=False, separators=(",", ":"))]])
                update_range(args.account, f"{TAB}!{updated_col}{sheet_row}:{updated_col}{sheet_row}", [[now]])
            updated += 1
            log(f"row {sheet_row} updated")
        except Exception as exc:
            errors += 1
            log(f"row {sheet_row} error: {exc!r}")

        save_progress({
            "status": "running",
            "candidates": len(candidates),
            "updated": updated,
            "errors": errors,
            "lastRow": sheet_row,
            "lastCourseCode": course_code,
            "lastCourseName": course_name,
            "dryRun": args.dry_run,
        })

        if n < len(candidates):
            delay = random.uniform(args.row_gap_low, args.row_gap_high)
            log(f"sleeping {delay:.1f}s before next row")
            time.sleep(delay)

    save_progress({
        "status": "completed-dry-run" if args.dry_run else "completed",
        "candidates": len(candidates),
        "updated": updated,
        "errors": errors,
        "finishedAt": now_lisbon(),
        "dryRun": args.dry_run,
    })
    log(f"done :: updated={updated} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
