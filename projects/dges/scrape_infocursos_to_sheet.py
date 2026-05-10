#!/usr/bin/env python3
"""Scrape InfoCursos stats into the DGES Google Sheet.

Current implementation supports a controlled institution-sigla scope, defaulting to FEUP.
It preserves existing sheet data by updating only the configured InfoCursos JSON columns
and updated_at for matching rows.
"""

import argparse
import ast
import datetime as dt
import html as html_lib
import json
import os
import re
import subprocess
import time
import urllib.request
from zoneinfo import ZoneInfo

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
TAB = "dges_cursos_2026"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
INFOCURSOS_URL = "https://infocursos.medu.pt/dges.asp?code={code}&codc={codc}"

TARGET_HEADERS = [
    "infocursos_iefp_desemprego_json",
    "infocursos_taxa_conclusao_json",
    "infocursos_classificacoes_finais_json",
    "infocursos_sexo_curso_json",
    "infocursos_nacionalidade_curso_json",
    "infocursos_idades_json",
]


def sh(args):
    return subprocess.check_output(args, text=True)


def gog_base(account):
    return ["gog", "sheets"] + (["--account", account] if account else [])


def get_sheet(account):
    return json.loads(
        sh(gog_base(account) + ["get", SHEET_ID, f"{TAB}!A1:ZZ2000", "--json", "--no-input"])
    )["values"]


def update_range(account, range_a1, values):
    subprocess.run(
        gog_base(account)
        + [
            "update",
            SHEET_ID,
            range_a1,
            "--values-json",
            json.dumps(values, ensure_ascii=False),
            "--input",
            "USER_ENTERED",
            "--no-input",
        ],
        check=True,
    )


def column_letter(index_1_based):
    result = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        result = chr(65 + rem) + result
    return result


def js_array_to_py(value):
    value = value.replace("\xa0", " ")
    value = re.sub(r"\bnull\b", "None", value)
    return ast.literal_eval(value)


def extract_chart(page, number):
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
    rows = []
    for row in chart["rows"]:
        if keep_first_col_values is not None and row[0] not in keep_first_col_values:
            continue
        rows.append({labels[i] if i < len(labels) else f"col_{i + 1}": row[i] for i in range(min(len(row), len(labels)))})
    return rows


def div_text(page, div_id):
    match = re.search(rf"<div id='{re.escape(div_id)}'[^>]*>(.*?)</div>", page, re.S)
    if not match:
        return None
    text = re.sub("<.*?>", " ", match.group(1))
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def scrape_infocursos(institution_code, course_code):
    url = INFOCURSOS_URL.format(code=institution_code, codc=course_code)
    req = urllib.request.Request(url, headers={"User-Agent": "OpenClaw InfoCursos scraper/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        page = response.read().decode("iso-8859-1", "replace")

    no_stats = re.search(r"Este curso não tem estatísticas disponíveis[^<]*", page)
    if no_stats:
        unavailable = {"available": False, "message": html_lib.unescape(no_stats.group(0)).strip()}
        return [json.dumps(unavailable, ensure_ascii=False, separators=(",", ":")) for _ in TARGET_HEADERS]

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

    payloads = {
        "infocursos_iefp_desemprego_json": {"available": bool(unemployment), "rows": unemployment or []},
        "infocursos_taxa_conclusao_json": completion,
        "infocursos_classificacoes_finais_json": {"available": bool(classifications), "rows": classifications or []},
        "infocursos_sexo_curso_json": {"available": bool(sex), "rows": sex or []},
        "infocursos_nacionalidade_curso_json": {"available": bool(nationality), "rows": nationality or []},
        "infocursos_idades_json": {"available": bool(ages), "rows": ages or []},
    }
    return [json.dumps(payloads[header], ensure_ascii=False, separators=(",", ":")) for header in TARGET_HEADERS]


def timestamp_lisbon():
    return dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=os.environ.get("GOG_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--institution-sigla", default="FEUP")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sleep", type=float, default=0.3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    values = get_sheet(args.account)
    headers = values[0]
    header_index = {name: index for index, name in enumerate(headers)}

    required = ["updated_at", "course_code", "institution_code", "institution_sigla", *TARGET_HEADERS]
    missing = [name for name in required if name not in header_index]
    if missing:
        raise SystemExit(f"Missing required columns: {', '.join(missing)}")

    target_start = header_index[TARGET_HEADERS[0]] + 1
    target_end = header_index[TARGET_HEADERS[-1]] + 1
    target_range_cols = f"{column_letter(target_start)}: {column_letter(target_end)}"
    now = timestamp_lisbon()

    matched = []
    for sheet_row, row in enumerate(values[1:], start=2):
        sigla = row[header_index["institution_sigla"]] if len(row) > header_index["institution_sigla"] else ""
        if sigla == args.institution_sigla:
            matched.append((sheet_row, row))
            if args.limit and len(matched) >= args.limit:
                break

    print(f"Matched {len(matched)} rows for {args.institution_sigla}")
    for n, (sheet_row, row) in enumerate(matched, start=1):
        course_code = row[header_index["course_code"]]
        institution_code = row[header_index["institution_code"]]
        print(f"[{n}/{len(matched)}] row {sheet_row}: {institution_code}/{course_code}")
        scraped = scrape_infocursos(institution_code, course_code)
        if args.dry_run:
            continue
        update_range(args.account, f"{TAB}!A{sheet_row}:A{sheet_row}", [[now]])
        update_range(
            args.account,
            f"{TAB}!{column_letter(target_start)}{sheet_row}:{column_letter(target_end)}{sheet_row}",
            [scraped],
        )
        time.sleep(args.sleep)

    print(json.dumps({"updated_at": now, "matched": len(matched), "dry_run": args.dry_run}, ensure_ascii=False))


if __name__ == "__main__":
    main()
