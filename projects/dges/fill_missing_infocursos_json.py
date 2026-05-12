#!/usr/bin/env python3
"""Fill missing InfoCursos JSON columns conservatively.

Behavior:
- reads the sheet headers live and maps columns by name on every run
- only writes into currently empty target cells
- only writes a JSON payload when the scrape for that specific chart succeeds
- if a chart is unavailable / cannot be parsed, the target cell stays empty
- updates updated_at only when at least one target field in the row is filled
"""

from __future__ import annotations

import argparse
import ast
import datetime as dt
import html as html_lib
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
LOG_PATH = DATA_DIR / "fill_missing_infocursos_json.log"
PROGRESS_PATH = DATA_DIR / "fill_missing_infocursos_json_progress.json"
CACHE_PATH = DATA_DIR / "fill_missing_infocursos_json_cache.json"
TARGET_HEADERS = [
    "infocursos_iefp_desemprego_json",
    "infocursos_classificacoes_finais_json",
    "infocursos_sexo_curso_json",
    "infocursos_nacionalidade_curso_json",
    "infocursos_idades_json",
]
UPDATED_AT_HEADER = "updated_at"


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


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def sh(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def gog_base(account: str) -> list[str]:
    return ["gog", "sheets", "--account", account]


def get_sheet(account: str) -> list[list[str]]:
    return json.loads(
        sh(gog_base(account) + ["get", SHEET_ID, f"{TAB}!A1:ZZ2000", "--json", "--no-input"])
    )["values"]


def update_range(account: str, a1_range: str, values: list[list[str]]) -> None:
    cmd = gog_base(account) + [
        "update",
        SHEET_ID,
        a1_range,
        "--values-json",
        json.dumps(values, ensure_ascii=False),
        "--input",
        "USER_ENTERED",
        "--no-input",
    ]
    for attempt in range(6):
        try:
            subprocess.run(cmd, check=True)
            return
        except subprocess.CalledProcessError as exc:
            if attempt >= 5:
                raise
            wait_seconds = min(90, (2 ** attempt) * 10) + random.uniform(0, 3)
            log(
                f"write retry for {a1_range} after error (attempt {attempt + 1}/6, exit={exc.returncode}); "
                f"sleeping {wait_seconds:.1f}s"
            )
            time.sleep(wait_seconds)


def column_letter(index_1_based: int) -> str:
    result = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def set_row_value(row: list[str], index: int, value: str) -> None:
    while len(row) <= index:
        row.append("")
    row[index] = value


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Nyx infocursos-json/1.0)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("iso-8859-1", "replace")


def js_array_to_py(value: str):
    value = value.replace("\xa0", " ")
    value = re.sub(r"\bnull\b", "None", value)
    return ast.literal_eval(value)


def extract_chart(page: str, number: int):
    match = re.search(
        rf"function\s+drawChart{number}\s*\(\)\s*\{{(.*?)\}}\s*(?:google\.setOnLoadCallback|</script>)",
        page,
        re.S,
    )
    if not match:
        return None
    block = match.group(1)
    columns = [
        {"type": m.group(1), "label": m.group(2)}
        for m in re.finditer(r"data\.addColumn\('([^']+)'\s*,\s*'([^']+)'\);", block)
    ]
    rows_match = re.search(r"data\.addRows\((\[.*?\])\);", block, re.S)
    if not rows_match:
        return None
    return {"columns": columns, "rows": js_array_to_py(rows_match.group(1))}


def rows_as_objects(chart, keep_first_col_values=None):
    if not chart:
        return None
    labels = [column["label"] for column in chart["columns"]]
    out = []
    for row in chart["rows"]:
        if keep_first_col_values is not None and row[0] not in keep_first_col_values:
            continue
        out.append({labels[i] if i < len(labels) else f"col_{i + 1}": row[i] for i in range(min(len(row), len(labels)))})
    return out


def compact_json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def scrape_payloads(stats_url: str, cache: dict) -> dict[str, str]:
    cached = cache.get("stats_pages", {}).get(stats_url)
    if cached is None:
        page = fetch(stats_url)
        cache.setdefault("stats_pages", {})[stats_url] = page
    else:
        page = cached

    # If InfoCursos itself says no stats, keep all target cells empty.
    no_stats = re.search(r"Este curso não tem estatísticas disponíveis[^<]*", page)
    if no_stats:
        return {}

    payloads: dict[str, str] = {}

    unemployment = rows_as_objects(extract_chart(page, 9), keep_first_col_values={"Curso"})
    if unemployment:
        payloads["infocursos_iefp_desemprego_json"] = compact_json({"available": True, "rows": unemployment})

    final_grades = rows_as_objects(extract_chart(page, 7))
    if final_grades:
        payloads["infocursos_classificacoes_finais_json"] = compact_json({"available": True, "rows": final_grades})

    sex = rows_as_objects(extract_chart(page, 4), keep_first_col_values={"Curso"})
    if sex:
        payloads["infocursos_sexo_curso_json"] = compact_json({"available": True, "rows": sex})

    nationality = rows_as_objects(extract_chart(page, 6), keep_first_col_values={"Curso"})
    if nationality:
        payloads["infocursos_nacionalidade_curso_json"] = compact_json({"available": True, "rows": nationality})

    ages = rows_as_objects(extract_chart(page, 5))
    if ages:
        payloads["infocursos_idades_json"] = compact_json({"available": True, "rows": ages})

    return payloads


def flush_dirty_rows(account: str, values: list[list[str]], idx: dict[str, int], dirty_rows: list[int], chunk_rows: int = 10) -> None:
    if not dirty_rows:
        return

    sorted_rows = sorted(set(dirty_rows))
    batches: list[tuple[int, int]] = []
    start = prev = sorted_rows[0]

    def add_range(s: int, e: int) -> None:
        cursor = s
        while cursor <= e:
            end = min(cursor + chunk_rows - 1, e)
            batches.append((cursor, end))
            cursor = end + 1

    for row_num in sorted_rows[1:]:
        if row_num == prev + 1 and (row_num - start + 1) <= chunk_rows:
            prev = row_num
            continue
        add_range(start, prev)
        start = prev = row_num
    add_range(start, prev)

    target_start = idx[TARGET_HEADERS[0]] + 1
    target_end = idx[TARGET_HEADERS[-1]] + 1
    updated_col = idx[UPDATED_AT_HEADER] + 1

    for start, end in batches:
        update_range(
            account,
            f"{TAB}!{column_letter(updated_col)}{start}:{column_letter(updated_col)}{end}",
            [[values[row_num - 1][idx[UPDATED_AT_HEADER]] if len(values[row_num - 1]) > idx[UPDATED_AT_HEADER] else ""] for row_num in range(start, end + 1)],
        )
        update_range(
            account,
            f"{TAB}!{column_letter(target_start)}{start}:{column_letter(target_end)}{end}",
            [[values[row_num - 1][idx[header]] if len(values[row_num - 1]) > idx[header] else "" for header in TARGET_HEADERS] for row_num in range(start, end + 1)],
        )


def row_value(row: list[str], idx: dict[str, int], header: str) -> str:
    return str(row[idx[header]]).strip() if len(row) > idx[header] else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=os.environ.get("GOG_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--flush-every", type=int, default=80)
    parser.add_argument("--request-gap-low", type=float, default=0.2)
    parser.add_argument("--request-gap-high", type=float, default=0.7)
    args = parser.parse_args()

    ensure_dirs()
    cache = load_json(CACHE_PATH, {"stats_pages": {}})
    values = get_sheet(args.account)
    headers = values[0]
    idx = {header: i for i, header in enumerate(headers)}

    required = [UPDATED_AT_HEADER, "course_code", "course_name", "institution_name", "estatisticas_do_curso", *TARGET_HEADERS]
    missing_headers = [header for header in required if header not in idx]
    if missing_headers:
        raise SystemExit(f"Missing required columns: {', '.join(missing_headers)}")

    header_positions = {header: idx[header] + 1 for header in [UPDATED_AT_HEADER, *TARGET_HEADERS]}
    candidates = []
    for sheet_row, row in enumerate(values[1:], start=2):
        if any(not row_value(row, idx, header) for header in TARGET_HEADERS):
            candidates.append((sheet_row, row))

    if args.limit:
        candidates = candidates[: args.limit]

    field_fills = {header: 0 for header in TARGET_HEADERS}
    save_progress(
        {
            "status": "starting",
            "sheet_id": SHEET_ID,
            "tab": TAB,
            "header_positions": header_positions,
            "candidates": len(candidates),
            "processed": 0,
            "changed_rows": 0,
            "field_fills": field_fills,
            "errors": 0,
            "log_path": str(LOG_PATH.resolve()),
            "cache_path": str(CACHE_PATH.resolve()),
            "dryRun": args.dry_run,
            "startedAt": now_lisbon(),
        }
    )
    log(f"live header mapping: {json.dumps(header_positions, ensure_ascii=False)}")
    log(f"candidate rows: {len(candidates)}")

    processed = 0
    changed_rows = 0
    errors = 0
    dirty_rows: list[int] = []

    for n, (sheet_row, row) in enumerate(candidates, start=1):
        course_code = row_value(row, idx, "course_code")
        course_name = row_value(row, idx, "course_name")
        institution_name = row_value(row, idx, "institution_name")
        stats_url = row_value(row, idx, "estatisticas_do_curso")
        missing_now = [header for header in TARGET_HEADERS if not row_value(row, idx, header)]
        log(f"[{n}/{len(candidates)}] row {sheet_row} :: {course_code} :: {course_name} :: {institution_name} :: missing={','.join(missing_now)}")
        try:
            if not stats_url:
                log(f"row {sheet_row} skipped: missing estatisticas_do_curso")
            else:
                payloads = scrape_payloads(stats_url, cache)
                row_changed = False
                filled_headers = []
                for header in TARGET_HEADERS:
                    if row_value(row, idx, header):
                        continue
                    payload = payloads.get(header)
                    if not payload:
                        continue
                    if not args.dry_run:
                        set_row_value(row, idx[header], payload)
                    field_fills[header] += 1
                    filled_headers.append(header)
                    row_changed = True

                if row_changed:
                    if not args.dry_run:
                        set_row_value(row, idx[UPDATED_AT_HEADER], now_lisbon())
                    changed_rows += 1
                    if not args.dry_run:
                        dirty_rows.append(sheet_row)
                    log(f"row {sheet_row} prepared :: filled={filled_headers}")
                else:
                    log(f"row {sheet_row} unchanged")

                save_json(CACHE_PATH, cache)
                time.sleep(random.uniform(args.request_gap_low, args.request_gap_high))

            processed += 1
        except Exception as exc:
            errors += 1
            log(f"row {sheet_row} error: {exc!r}")

        if dirty_rows and processed % args.flush_every == 0:
            flush_dirty_rows(args.account, values, idx, dirty_rows)
            dirty_rows = []
            log(f"flushed dirty rows after {processed} processed rows")

        save_progress(
            {
                "status": "running",
                "sheet_id": SHEET_ID,
                "tab": TAB,
                "header_positions": header_positions,
                "candidates": len(candidates),
                "processed": processed,
                "changed_rows": changed_rows,
                "field_fills": field_fills,
                "errors": errors,
                "remaining": len(candidates) - processed,
                "lastRow": sheet_row,
                "lastCourseCode": course_code,
                "lastCourseName": course_name,
                "lastInstitutionName": institution_name,
                "log_path": str(LOG_PATH.resolve()),
                "cache_path": str(CACHE_PATH.resolve()),
                "dryRun": args.dry_run,
                "updatedAt": now_lisbon(),
            }
        )

    if dirty_rows:
        flush_dirty_rows(args.account, values, idx, dirty_rows)
        log(f"final flush complete after {processed} processed rows")

    save_json(CACHE_PATH, cache)
    save_progress(
        {
            "status": "completed-dry-run" if args.dry_run else "completed",
            "sheet_id": SHEET_ID,
            "tab": TAB,
            "header_positions": header_positions,
            "candidates": len(candidates),
            "processed": processed,
            "changed_rows": changed_rows,
            "field_fills": field_fills,
            "errors": errors,
            "remaining": len(candidates) - processed,
            "finishedAt": now_lisbon(),
            "log_path": str(LOG_PATH.resolve()),
            "cache_path": str(CACHE_PATH.resolve()),
            "dryRun": args.dry_run,
        }
    )
    log(f"done :: processed={processed} changed_rows={changed_rows} errors={errors} field_fills={json.dumps(field_fills, ensure_ascii=False)}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
