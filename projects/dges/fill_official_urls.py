#!/usr/bin/env python3
"""Fill institution_url and course_url columns in the DGES sheet.

- institution_url: official institution / faculty page from DGES detail page contact block
- course_url: official course page from the InfoCursos statistics page button when available

The script is intentionally conservative and suitable for small recurring batches.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
TAB = "dges_cursos_2026"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
DATA_DIR = Path("projects/dges/data")
CACHE_PATH = DATA_DIR / "official_urls_cache.json"
LOG_PATH = DATA_DIR / "fill_official_urls.log"
PROGRESS_PATH = DATA_DIR / "fill_official_urls_progress.json"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def now_lisbon() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")


def log(msg: str) -> None:
    line = f"[{now_lisbon()}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def save_progress(payload: dict) -> None:
    PROGRESS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {"institution_url": {}}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


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


def set_row_value(row: list[str], index: int, value: str) -> None:
    while len(row) <= index:
        row.append("")
    row[index] = value


def flush_sheet_columns(
    account: str,
    values: list[list[str]],
    updated_idx: int,
    institution_idx: int,
    course_idx: int,
) -> None:
    last_sheet_row = len(values)
    update_range(
        account,
        f"{TAB}!{column_letter(updated_idx + 1)}2:{column_letter(updated_idx + 1)}{last_sheet_row}",
        [[row[updated_idx] if len(row) > updated_idx else ""] for row in values[1:]],
    )
    update_range(
        account,
        f"{TAB}!{column_letter(institution_idx + 1)}2:{column_letter(institution_idx + 1)}{last_sheet_row}",
        [[row[institution_idx] if len(row) > institution_idx else ""] for row in values[1:]],
    )
    update_range(
        account,
        f"{TAB}!{column_letter(course_idx + 1)}2:{column_letter(course_idx + 1)}{last_sheet_row}",
        [[row[course_idx] if len(row) > course_idx else ""] for row in values[1:]],
    )


def column_letter(index_1_based: int) -> str:
    result = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Nyx official-links/1.0)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("iso-8859-1", "replace")


def extract_institution_url(details_html: str) -> str:
    m = re.search(r"Endere(?:ç|&ccedil;)o e Contactos da Institui(?:ç|&ccedil;)ão</h2>\s*(.*?)<h2>", details_html, re.S | re.I)
    block = m.group(1) if m else details_html
    for href in re.findall(r"href='([^']+)'", block, re.I):
        if href.startswith("mailto:"):
            continue
        if "maps.google" in href:
            continue
        if href.startswith("http"):
            return href
    return ""


def extract_course_url(stats_html: str) -> str:
    m = re.search(r"<a href='([^']+)' target=_blank class='btnAzul'>Página do curso na instituição</a>", stats_html, re.I)
    return m.group(1) if m else ""


def main() -> int:
    global CACHE_PATH, LOG_PATH, PROGRESS_PATH

    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=os.environ.get("GOG_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--modulus", type=int, default=None)
    parser.add_argument("--remainder", type=int, default=0)
    parser.add_argument("--cache-path", default=None)
    parser.add_argument("--log-path", default=None)
    parser.add_argument("--progress-path", default=None)
    parser.add_argument("--flush-every", type=int, default=100)
    parser.add_argument("--request-gap-low", type=float, default=2.0)
    parser.add_argument("--request-gap-high", type=float, default=4.0)
    parser.add_argument("--row-gap-low", type=float, default=5.0)
    parser.add_argument("--row-gap-high", type=float, default=10.0)
    args = parser.parse_args()

    if args.modulus is not None:
        if args.modulus <= 0:
            raise SystemExit("--modulus must be > 0")
        if args.remainder < 0 or args.remainder >= args.modulus:
            raise SystemExit("--remainder must be >= 0 and < --modulus")

    if args.cache_path:
        CACHE_PATH = Path(args.cache_path)
    if args.log_path:
        LOG_PATH = Path(args.log_path)
    if args.progress_path:
        PROGRESS_PATH = Path(args.progress_path)

    ensure_dirs()
    cache = load_cache()
    values = get_sheet(args.account)
    headers = values[0]
    idx = {header: i for i, header in enumerate(headers)}
    required = ["updated_at", "institution_name", "detalhes_do_curso", "estatisticas_do_curso", "institution_url", "course_url"]
    missing = [name for name in required if name not in idx]
    if missing:
        raise SystemExit(f"Missing required columns: {', '.join(missing)}")

    if args.flush_every <= 0:
        raise SystemExit("--flush-every must be > 0")

    candidates = []
    for sheet_row, row in enumerate(values[1:], start=2):
        institution_url = row[idx["institution_url"]] if len(row) > idx["institution_url"] else ""
        course_url = row[idx["course_url"]] if len(row) > idx["course_url"] else ""
        if not institution_url or not course_url:
            if args.modulus is not None and sheet_row % args.modulus != args.remainder:
                continue
            candidates.append((sheet_row, row))
    if args.limit:
        candidates = candidates[: args.limit]

    log(f"candidate rows: {len(candidates)}")
    save_progress({"status": "starting", "candidates": len(candidates), "updated": 0, "errors": 0, "dryRun": args.dry_run})

    processed = 0
    changed = 0
    errors = 0
    dirty = False
    for n, (sheet_row, row) in enumerate(candidates, start=1):
        name = row[idx["institution_name"]] if len(row) > idx["institution_name"] else ""
        details_url = row[idx["detalhes_do_curso"]] if len(row) > idx["detalhes_do_curso"] else ""
        stats_url = row[idx["estatisticas_do_curso"]] if len(row) > idx["estatisticas_do_curso"] else ""
        current_institution_url = row[idx["institution_url"]] if len(row) > idx["institution_url"] else ""
        current_course_url = row[idx["course_url"]] if len(row) > idx["course_url"] else ""
        log(f"[{n}/{len(candidates)}] row {sheet_row} :: {name}")
        try:
            institution_url = current_institution_url
            if not institution_url:
                institution_url = cache["institution_url"].get(name, "")
            if not institution_url and details_url:
                details_html = fetch(details_url)
                institution_url = extract_institution_url(details_html)
                cache["institution_url"][name] = institution_url
                save_cache(cache)
                time.sleep(random.uniform(args.request_gap_low, args.request_gap_high))

            course_url = current_course_url
            if not course_url and stats_url:
                stats_html = fetch(stats_url)
                course_url = extract_course_url(stats_html)

            if not args.dry_run:
                row_changed = False
                if institution_url != current_institution_url:
                    set_row_value(row, idx["institution_url"], institution_url)
                    row_changed = True
                if course_url != current_course_url:
                    set_row_value(row, idx["course_url"], course_url)
                    row_changed = True
                if row_changed:
                    set_row_value(row, idx["updated_at"], now_lisbon())
                    changed += 1
                    dirty = True
            processed += 1
            log(f"row {sheet_row} updated :: institution_url={bool(institution_url)} course_url={bool(course_url)}")
        except Exception as exc:
            errors += 1
            log(f"row {sheet_row} error: {exc!r}")

        if not args.dry_run and dirty and processed % args.flush_every == 0:
            flush_sheet_columns(args.account, values, idx["updated_at"], idx["institution_url"], idx["course_url"])
            dirty = False
            log(f"flushed sheet columns after {processed} processed rows")

        save_progress({
            "status": "running",
            "candidates": len(candidates),
            "processed": processed,
            "changed": changed,
            "errors": errors,
            "lastRow": sheet_row,
            "lastInstitutionName": name,
            "dryRun": args.dry_run,
        })
        if n < len(candidates):
            delay = random.uniform(args.row_gap_low, args.row_gap_high)
            log(f"sleeping {delay:.1f}s before next row")
            time.sleep(delay)

    if not args.dry_run and dirty:
        flush_sheet_columns(args.account, values, idx["updated_at"], idx["institution_url"], idx["course_url"])
        log(f"final flush complete after {processed} processed rows")

    save_progress({
        "status": "completed-dry-run" if args.dry_run else "completed",
        "candidates": len(candidates),
        "processed": processed,
        "changed": changed,
        "errors": errors,
        "finishedAt": now_lisbon(),
        "dryRun": args.dry_run,
    })
    log(f"done :: processed={processed} changed={changed} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
