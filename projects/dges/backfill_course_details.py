#!/usr/bin/env python3
"""Backfill DGES course-detail fields from detalhes_do_curso URLs.

The script is intentionally resumable and conservative:
- appends missing target columns at the end of dges_cursos_2026
- writes only those target columns plus updated_at
- skips rows whose target columns are already complete
- keeps progress/cache/log state under projects/dges/data/
- maintains an area_cnaef tab with a unique sorted list
"""

from __future__ import annotations

import argparse
import datetime as dt
import html as html_lib
import json
import os
import random
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
TAB = "dges_cursos_2026"
AREA_TAB = "area_cnaef"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
DATA_DIR = Path("projects/dges/data")
LOG_PATH = DATA_DIR / "backfill_course_details.log"
PROGRESS_PATH = DATA_DIR / "backfill_course_details_progress.json"
CACHE_PATH = DATA_DIR / "backfill_course_details_cache.json"

DETAIL_HEADERS = [
    "Telefone",
    "Area CNAEF",
    "Duração",
    "ECTS",
    "Tipo de Ensino",
    "Concurso",
    "Vagas",
    "Provas de Ingresso",
    "Classificações Mínimas",
]


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def now_lisbon() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")


def log(message: str) -> None:
    line = f"[{now_lisbon()}] {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_progress(payload: dict) -> None:
    save_json(PROGRESS_PATH, payload)


def compact_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def sh(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def gog_base(account: str) -> list[str]:
    return ["gog", "sheets", "--account", account]


def get_sheet(account: str, range_a1: str) -> list[list[str]]:
    payload = json.loads(sh(gog_base(account) + ["get", SHEET_ID, range_a1, "--json", "--no-input"]))
    return payload.get("values", [])


def update_range(account: str, range_a1: str, values: list[list[str]], dry_run: bool) -> None:
    if dry_run:
        log(f"dry-run update {range_a1} rows={len(values)}")
        return
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


def add_tab(account: str, tab_name: str, dry_run: bool) -> None:
    if dry_run:
        log(f"dry-run add-tab {tab_name}")
        return
    subprocess.run(gog_base(account) + ["add-tab", SHEET_ID, tab_name, "--no-input"], check=True)


def metadata(account: str) -> dict:
    return json.loads(sh(gog_base(account) + ["metadata", SHEET_ID, "--json", "--no-input"]))


def column_letter(index_1_based: int) -> str:
    out = ""
    n = index_1_based
    while n:
        n, rem = divmod(n - 1, 26)
        out = chr(65 + rem) + out
    return out


def clean_text(value: str) -> str:
    value = html_lib.unescape(value or "").replace("\xa0", " ")
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<.*?>", " ", value, flags=re.S)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    value = re.sub(r"\n{2,}", "\n", value)
    return value.strip()


def strip_spaces(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def fetch(url: str, timeout: int = 30, retries: int = 3) -> str:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Nyx DGES detail backfill/1.0)",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.6",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode("iso-8859-1", "replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(5 * attempt + random.uniform(0.5, 3.0))
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def extract_first(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.S | re.I)
    return strip_spaces(match.group(1)) if match else ""


def section_html(page: str, title: str) -> str:
    pattern = rf"<h2>\s*{re.escape(title)}\s*</h2>(.*?)(?=<h2>|<a name='lev\d+'|</body>|$)"
    match = re.search(pattern, page, re.S | re.I)
    return match.group(1) if match else ""


def parse_provas(page: str) -> dict:
    text = clean_text(section_html(page, "Provas de Ingresso"))
    sets: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    for raw_line in text.splitlines():
        line = strip_spaces(raw_line)
        if not line or "seguintes conjuntos" in line.casefold():
            continue
        if line.casefold() == "ou":
            if current:
                sets.append(current)
                current = []
            continue
        match = re.match(r"^([0-9]{2})\s+(.+)$", line)
        if match:
            current.append({"code": match.group(1), "name": strip_spaces(match.group(2))})
    if current:
        sets.append(current)

    all_codes = sorted({exam["code"] for group in sets for exam in group})
    all_names = sorted({exam["name"] for group in sets for exam in group})
    return {"sets": sets, "all_codes": all_codes, "all_names": all_names, "raw": text}


def parse_classificacoes_minimas(page: str) -> dict:
    text = clean_text(section_html(page, "Classificações Mínimas"))
    out: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = strip_spaces(raw_line)
        match = re.match(r"^([^:]+):\s*([0-9,.]+)\s*pontos?", line, re.I)
        if match:
            key = match.group(1).strip().casefold().replace(" ", "_")
            out[key] = match.group(2).replace(",", ".")
    out["raw"] = text
    return out


def parse_vagas(page: str, plain: str) -> dict:
    current: dict[str, str | int] = {}
    current_match = re.search(r"Vagas\s+para\s+([0-9]{4}-[0-9]{4}):\s*([0-9]+)", plain, re.I)
    if current_match:
        current = {"year": current_match.group(1), "vagas": int(current_match.group(2))}

    historical: dict[str, dict[str, str]] = {}
    start = page.find('summary="Dados de anos anteriores"')
    if start != -1:
        table_start = page.rfind("<table", 0, start)
        table_end = page.find("</table>", start)
        table = page[table_start : table_end + 8] if table_start != -1 and table_end != -1 else ""
        years = re.findall(r"<th[^>]*colspan=['\"]2['\"][^>]*>\s*([0-9]{4})\s*</th>", table, re.I)
        vagas_match = re.search(r"<strong>\s*Vagas\s*</strong>\s*</th>(.*?)</tr>", table, re.S | re.I)
        if years and vagas_match:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", vagas_match.group(1), re.S | re.I)
            values = [strip_spaces(clean_text(cell)) for cell in cells]
            for i, year in enumerate(years):
                historical[year] = {
                    "1a": values[i * 2] if i * 2 < len(values) else "",
                    "2a": values[i * 2 + 1] if i * 2 + 1 < len(values) else "",
                }
    return {"current": current, "historical": historical}


def parse_details(page: str) -> dict[str, str]:
    plain = clean_text(page)
    parsed = {
        "Telefone": extract_first(r"\bTel:\s*([^\n]+)", plain),
        "Area CNAEF": extract_first(r"Área\s+CNAEF:\s*([^\n]+)", plain),
        "Duração": extract_first(r"Duração:\s*([^\n]+)", plain),
        "ECTS": extract_first(r"ECTS:\s*([^\n]+)", plain),
        "Tipo de Ensino": extract_first(r"Tipo\s+de\s+Ensino:\s*([^\n]+)", plain),
        "Concurso": extract_first(r"Concurso:\s*([^\n]+)", plain),
    }
    parsed["Vagas"] = compact_json(parse_vagas(page, plain))
    parsed["Provas de Ingresso"] = compact_json(parse_provas(page))
    parsed["Classificações Mínimas"] = compact_json(parse_classificacoes_minimas(page))
    return parsed


def row_value(row: list[str], idx: dict[str, int], header: str) -> str:
    pos = idx[header]
    return str(row[pos]).strip() if len(row) > pos else ""


def set_row_value(row: list[str], idx: dict[str, int], header: str, value: str) -> None:
    pos = idx[header]
    while len(row) <= pos:
        row.append("")
    row[pos] = value


def row_complete(row: list[str], idx: dict[str, int]) -> bool:
    return all(row_value(row, idx, header) for header in DETAIL_HEADERS)


def ensure_headers(account: str, values: list[list[str]], dry_run: bool) -> tuple[list[list[str]], dict[str, int]]:
    headers = values[0][:]
    changed = False
    for header in DETAIL_HEADERS:
        if header not in headers:
            headers.append(header)
            changed = True
    if changed:
        end_col = column_letter(len(headers))
        update_range(account, f"{TAB}!A1:{end_col}1", [headers], dry_run)
        values[0] = headers
        log(f"headers appended through {end_col}: {', '.join([h for h in DETAIL_HEADERS if h in headers])}")
    return values, {header: i for i, header in enumerate(headers)}


def ensure_area_tab(account: str, meta: dict, dry_run: bool) -> None:
    existing = {sheet["properties"]["title"] for sheet in meta.get("sheets", [])}
    if AREA_TAB not in existing:
        add_tab(account, AREA_TAB, dry_run)
        log(f"created tab {AREA_TAB}")


def read_existing_areas(account: str) -> set[str]:
    try:
        rows = get_sheet(account, f"{AREA_TAB}!A1:A2000")
    except subprocess.CalledProcessError:
        return set()
    if not rows:
        return set()
    values = {strip_spaces(row[0]) for row in rows[1:] if row and strip_spaces(row[0])}
    return values


def update_area_tab(account: str, areas: set[str], dry_run: bool) -> None:
    rows = [["Area CNAEF"]] + [[area] for area in sorted(areas, key=lambda v: v.casefold())]
    update_range(account, f"{AREA_TAB}!A1:A{len(rows)}", rows, dry_run)


def flush_rows(account: str, rows: list[tuple[int, list[str]]], idx: dict[str, int], dry_run: bool) -> None:
    if not rows:
        return
    detail_start = idx[DETAIL_HEADERS[0]] + 1
    detail_end = idx[DETAIL_HEADERS[-1]] + 1
    detail_start_col = column_letter(detail_start)
    detail_end_col = column_letter(detail_end)

    run: list[tuple[int, list[str]]] = []

    def flush_run(items: list[tuple[int, list[str]]]) -> None:
        if not items:
            return
        first = items[0][0]
        last = items[-1][0]
        detail_values = [[row[idx[h]] if len(row) > idx[h] else "" for h in DETAIL_HEADERS] for _, row in items]
        updated_values = [[row[idx["updated_at"]] if len(row) > idx["updated_at"] else ""] for _, row in items]
        update_range(account, f"{TAB}!{detail_start_col}{first}:{detail_end_col}{last}", detail_values, dry_run)
        update_range(account, f"{TAB}!A{first}:A{last}", updated_values, dry_run)

    previous = None
    for sheet_row, row in rows:
        if previous is not None and sheet_row != previous + 1:
            flush_run(run)
            run = []
        run.append((sheet_row, row))
        previous = sheet_row
    flush_run(run)


def sleep_between_rows(low: float, high: float) -> None:
    delay = random.uniform(low, high)
    log(f"sleeping {delay:.1f}s before next row")
    time.sleep(delay)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=os.environ.get("GOG_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--row-gap-low", type=float, default=8.0)
    parser.add_argument("--row-gap-high", type=float, default=18.0)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--batch-rest-low", type=float, default=120.0)
    parser.add_argument("--batch-rest-high", type=float, default=300.0)
    args = parser.parse_args()

    ensure_dirs()
    cache: dict[str, dict[str, str]] = load_json(CACHE_PATH, {})
    log(f"loading sheet {TAB}")
    values = get_sheet(args.account, f"{TAB}!A1:ZZ2000")
    if not values:
        raise RuntimeError("sheet is empty")
    meta = metadata(args.account)
    ensure_area_tab(args.account, meta, args.dry_run)
    values, idx = ensure_headers(args.account, values, args.dry_run)

    required = ["updated_at", "course_code", "institution_code", "detalhes_do_curso", *DETAIL_HEADERS]
    missing = [header for header in required if header not in idx]
    if missing:
        raise RuntimeError(f"missing required columns: {', '.join(missing)}")

    candidates = []
    for offset, row in enumerate(values[1:], start=2):
        details_url = row_value(row, idx, "detalhes_do_curso")
        if details_url and not row_complete(row, idx):
            candidates.append((offset, row))

    if args.limit is not None:
        candidates = candidates[: args.limit]

    existing_areas = read_existing_areas(args.account)
    total = len(candidates)
    log(f"starting course-detail backfill :: candidates={total} :: dry_run={args.dry_run}")
    save_progress(
        {
            "updated_at": now_lisbon(),
            "sheet_id": SHEET_ID,
            "tab": TAB,
            "status": "running",
            "total": total,
            "processed": 0,
            "written": 0,
            "errors": 0,
            "percent": 0,
        }
    )

    batch: list[tuple[int, list[str]]] = []
    processed = written = errors = 0
    areas = set(existing_areas)

    for sheet_row, row in candidates:
        details_url = row_value(row, idx, "detalhes_do_curso")
        try:
            if details_url in cache:
                details = cache[details_url]
            else:
                details = parse_details(fetch(details_url))
                cache[details_url] = details
                save_json(CACHE_PATH, cache)

            for header in DETAIL_HEADERS:
                set_row_value(row, idx, header, details.get(header, ""))
            set_row_value(row, idx, "updated_at", now_lisbon())
            area = strip_spaces(details.get("Area CNAEF", ""))
            if area:
                areas.add(area)
            batch.append((sheet_row, row))
            written += 1
        except Exception as exc:
            errors += 1
            log(f"row {sheet_row} failed {details_url}: {exc}")

        processed += 1
        percent = round((processed / total) * 100, 2) if total else 100.0
        save_progress(
            {
                "updated_at": now_lisbon(),
                "sheet_id": SHEET_ID,
                "tab": TAB,
                "status": "running",
                "total": total,
                "processed": processed,
                "written": written,
                "errors": errors,
                "percent": percent,
                "current_sheet_row": sheet_row,
                "log_path": str(LOG_PATH.resolve()),
                "cache_path": str(CACHE_PATH.resolve()),
            }
        )

        if len(batch) >= args.batch_size:
            flush_rows(args.account, batch, idx, args.dry_run)
            update_area_tab(args.account, areas, args.dry_run)
            log(f"progress {percent:.2f}% :: processed={processed}/{total} written={written} errors={errors}")
            batch = []
            if processed < total:
                rest = random.uniform(args.batch_rest_low, args.batch_rest_high)
                log(f"batch rest {rest:.1f}s")
                time.sleep(rest)
        elif processed < total:
            sleep_between_rows(args.row_gap_low, args.row_gap_high)

    flush_rows(args.account, batch, idx, args.dry_run)
    update_area_tab(args.account, areas, args.dry_run)
    save_progress(
        {
            "updated_at": now_lisbon(),
            "sheet_id": SHEET_ID,
            "tab": TAB,
            "status": "completed",
            "total": total,
            "processed": processed,
            "written": written,
            "errors": errors,
            "percent": 100.0,
            "area_cnaef_count": len(areas),
            "log_path": str(LOG_PATH.resolve()),
            "cache_path": str(CACHE_PATH.resolve()),
        }
    )
    log(f"completed course-detail backfill :: processed={processed} written={written} errors={errors} areas={len(areas)}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
