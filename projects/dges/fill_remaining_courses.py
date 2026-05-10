#!/usr/bin/env python3
"""Fill remaining DGES sheet rows with InfoCursos stats and a short course description.

Design goals:
- skip rows already filled for all target columns
- use conservative rate limiting to avoid hammering DGES sites
- derive the course description from official DGES course-detail fields
- update updated_at with Europe/Lisbon date+time when a row is written
- keep a small progress file under projects/dges/data/
"""

from __future__ import annotations

import ast
import datetime as dt
import html as html_lib
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
TAB = "dges_cursos_2026"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
DATA_DIR = Path("projects/dges/data")
LOG_PATH = DATA_DIR / "fill_remaining_courses.log"
PROGRESS_PATH = DATA_DIR / "fill_remaining_courses_progress.json"

TARGET_HEADERS = [
    "updated_at",
    "infocursos_iefp_desemprego_json",
    "infocursos_taxa_conclusao_json",
    "infocursos_classificacoes_finais_json",
    "infocursos_sexo_curso_json",
    "infocursos_nacionalidade_curso_json",
    "infocursos_idades_json",
    "course_description",
]

JSON_HEADERS = TARGET_HEADERS[1:-1]


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str) -> None:
    stamp = dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")
    line = f"[{stamp}] {msg}"
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


def now_lisbon() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Nyx/1.0; slow crawl)"})
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


def div_text(page: str, div_id: str):
    match = re.search(rf"<div id='{re.escape(div_id)}'[^>]*>(.*?)</div>", page, re.S)
    if not match:
        return None
    text = re.sub("<.*?>", " ", match.group(1))
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def compact_json(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def scrape_infocursos(stats_url: str) -> dict[str, str]:
    page = fetch(stats_url)
    no_stats = re.search(r"Este curso não tem estatísticas disponíveis[^<]*", page)
    if no_stats:
        unavailable = {"available": False, "message": html_lib.unescape(no_stats.group(0)).strip()}
        return {header: compact_json(unavailable) for header in JSON_HEADERS}

    unemployment = rows_as_objects(extract_chart(page, 9), keep_first_col_values={"Curso"})
    completion_rows = rows_as_objects(extract_chart(page, 8))
    classifications = rows_as_objects(extract_chart(page, 7))
    sex = rows_as_objects(extract_chart(page, 4), keep_first_col_values={"Curso"})
    nationality = rows_as_objects(extract_chart(page, 6), keep_first_col_values={"Curso"})
    ages = rows_as_objects(extract_chart(page, 5))

    if completion_rows is None:
        completion = {"available": False, "message": div_text(page, "DivChart7")}
    else:
        completion = {"available": True, "rows": completion_rows}

    return {
        "infocursos_iefp_desemprego_json": compact_json({"available": bool(unemployment), "rows": unemployment or []}),
        "infocursos_taxa_conclusao_json": compact_json(completion),
        "infocursos_classificacoes_finais_json": compact_json({"available": bool(classifications), "rows": classifications or []}),
        "infocursos_sexo_curso_json": compact_json({"available": bool(sex), "rows": sex or []}),
        "infocursos_nacionalidade_curso_json": compact_json({"available": bool(nationality), "rows": nationality or []}),
        "infocursos_idades_json": compact_json({"available": bool(ages), "rows": ages or []}),
    }


def extract_first(pattern: str, text: str):
    match = re.search(pattern, text, re.S)
    return match.group(1).strip() if match else None


def parse_detail_fields(details_html: str) -> dict[str, str | None]:
    return {
        "grau": extract_first(r"Grau:\s*([^<\n]+)", details_html),
        "area_cnaef": extract_first(r"Área CNAEF:\s*([^<\n]+)", details_html),
        "duracao": extract_first(r"Duração:\s*([^<\n]+)", details_html),
        "ects": extract_first(r"ECTS:\s*([^<\n]+)", details_html),
        "tipo_ensino": extract_first(r"Tipo de Ensino:\s*([^<\n]+)", details_html),
    }


def build_description(course_name: str, institution_name: str, details_url: str) -> str:
    html = fetch(details_url)
    fields = parse_detail_fields(html)
    grau = fields.get("grau")
    area = fields.get("area_cnaef")
    duracao = fields.get("duracao")
    ects = fields.get("ects")

    if grau and area and duracao and ects:
        return f"{grau} de {duracao.lower()} e {ects} ECTS na área {area}."
    if grau and area:
        return f"{grau} na área {area}."
    if grau and duracao and ects:
        return f"{grau} de {duracao.lower()} e {ects} ECTS."
    return ""


def sleep_between_rows(base_low: float, base_high: float) -> None:
    delay = random.uniform(base_low, base_high)
    log(f"sleeping {delay:.1f}s before next row")
    time.sleep(delay)


def sleep_between_requests(low: float, high: float) -> None:
    time.sleep(random.uniform(low, high))


def row_missing_targets(row: list[str], idx: dict[str, int]) -> bool:
    for header in TARGET_HEADERS:
        pos = idx[header]
        if len(row) <= pos or not str(row[pos]).strip():
            return True
    return False


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=os.environ.get("GOG_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--request-gap-low", type=float, default=2.5)
    parser.add_argument("--request-gap-high", type=float, default=5.5)
    parser.add_argument("--row-gap-low", type=float, default=6.0)
    parser.add_argument("--row-gap-high", type=float, default=12.0)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--batch-rest-low", type=float, default=90.0)
    parser.add_argument("--batch-rest-high", type=float, default=180.0)
    args = parser.parse_args()

    ensure_dirs()
    values = get_sheet(args.account)
    headers = values[0]
    idx = {header: i for i, header in enumerate(headers)}

    required = ["course_code", "course_name", "institution_name", "estatisticas_do_curso", "detalhes_do_curso", *TARGET_HEADERS]
    missing_headers = [header for header in required if header not in idx]
    if missing_headers:
        raise SystemExit(f"Missing required columns: {', '.join(missing_headers)}")

    json_start = idx[JSON_HEADERS[0]] + 1
    json_end = idx[JSON_HEADERS[-1]] + 1
    description_col = idx["course_description"] + 1
    updated_col = idx["updated_at"] + 1

    pending = []
    for sheet_row, row in enumerate(values[1:], start=2):
        if row_missing_targets(row, idx):
            pending.append((sheet_row, row))

    if args.limit:
        pending = pending[: args.limit]

    log(f"pending rows: {len(pending)}")
    save_progress({"status": "starting", "pendingRows": len(pending), "updated": 0, "errors": 0, "lastRow": None})

    updated = 0
    errors = 0

    for n, (sheet_row, row) in enumerate(pending, start=1):
        course_code = row[idx["course_code"]] if len(row) > idx["course_code"] else ""
        course_name = row[idx["course_name"]] if len(row) > idx["course_name"] else ""
        institution = row[idx["institution_name"]] if len(row) > idx["institution_name"] else ""
        stats_url = row[idx["estatisticas_do_curso"]] if len(row) > idx["estatisticas_do_curso"] else ""
        details_url = row[idx["detalhes_do_curso"]] if len(row) > idx["detalhes_do_curso"] else ""

        log(f"[{n}/{len(pending)}] row {sheet_row} :: {course_code} :: {course_name} :: {institution}")
        try:
            if not stats_url or not details_url:
                raise ValueError("missing source url")

            stats_payloads = scrape_infocursos(stats_url)
            sleep_between_requests(args.request_gap_low, args.request_gap_high)
            description = build_description(course_name, institution, details_url)
            now = now_lisbon()

            if args.dry_run:
                log(f"dry-run row {sheet_row} ok :: description_len={len(description)}")
            else:
                update_range(args.account, f"{TAB}!{column_letter(updated_col)}{sheet_row}:{column_letter(updated_col)}{sheet_row}", [[now]])
                update_range(
                    args.account,
                    f"{TAB}!{column_letter(json_start)}{sheet_row}:{column_letter(json_end)}{sheet_row}",
                    [[stats_payloads[header] for header in JSON_HEADERS]],
                )
                update_range(
                    args.account,
                    f"{TAB}!{column_letter(description_col)}{sheet_row}:{column_letter(description_col)}{sheet_row}",
                    [[description]],
                )
                log(f"row {sheet_row} updated")
            updated += 1
        except Exception as exc:
            errors += 1
            log(f"row {sheet_row} error: {exc!r}")

        save_progress(
            {
                "status": "running",
                "pendingRows": len(pending),
                "updated": updated,
                "errors": errors,
                "lastRow": sheet_row,
                "lastCourseCode": course_code,
                "lastCourseName": course_name,
                "dryRun": args.dry_run,
            }
        )

        if n < len(pending):
            if n % args.batch_size == 0:
                batch_rest = random.uniform(args.batch_rest_low, args.batch_rest_high)
                log(f"batch rest after {n} rows: sleeping {batch_rest:.1f}s")
                time.sleep(batch_rest)
            else:
                sleep_between_rows(args.row_gap_low, args.row_gap_high)

    final_status = "completed-dry-run" if args.dry_run else "completed"
    save_progress(
        {
            "status": final_status,
            "pendingRows": len(pending),
            "updated": updated,
            "errors": errors,
            "lastRow": pending[-1][0] if pending else None,
            "finishedAt": now_lisbon(),
            "dryRun": args.dry_run,
        }
    )
    log(f"done :: updated={updated} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
