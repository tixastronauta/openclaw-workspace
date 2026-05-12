#!/usr/bin/env python3
"""Fill missing city/district/address/institution URL/course URL fields in the DGES sheet.

Safety/behavior:
- maps sheet columns live by header name before writing
- writes only target columns plus updated_at
- prefers existing sheet values for the same institution before fetching
- fetches official DGES/InfoCursos pages only when needed
- keeps progress/log/cache files under projects/dges/data/
"""

from __future__ import annotations

import argparse
import collections
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
LOG_PATH = DATA_DIR / "fill_missing_course_fields.log"
PROGRESS_PATH = DATA_DIR / "fill_missing_course_fields_progress.json"
CACHE_PATH = DATA_DIR / "fill_missing_course_fields_cache.json"
OFFICIAL_URLS_CACHE_PATH = DATA_DIR / "official_urls_cache.json"
TARGET_HEADERS = ["updated_at", "cidade", "distrito", "morada", "institution_url", "course_url"]
INSTITUTION_HEADERS = ["cidade", "distrito", "morada", "institution_url"]


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


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Nyx fill-missing-course-fields/1.0)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("iso-8859-1", "replace")


def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip().casefold()


def clean_row_value(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def smart_city_case(value: str) -> str:
    value = clean_row_value(value)
    if not value:
        return ""
    words = []
    for word in value.split(" "):
        lower = word.lower()
        if lower in {"de", "do", "da", "dos", "das", "e"}:
            words.append(lower)
        elif "-" in word:
            words.append("-".join(part.capitalize() if part else part for part in lower.split("-")))
        else:
            words.append(lower.capitalize())
    result = " ".join(words)
    result = re.sub(r"\bD'([a-zà-ÿ])", lambda m: "D'" + m.group(1).upper(), result, flags=re.I)
    return result


def extract_institution_url(details_html: str) -> str:
    match = re.search(r"Endere(?:ç|&ccedil;)o e Contactos da Institui(?:ç|&ccedil;)ão</h2>\s*(.*?)<h2>", details_html, re.S | re.I)
    block = match.group(1) if match else details_html
    for href in re.findall(r"href='([^']+)'", block, re.I):
        if href.startswith("mailto:"):
            continue
        if "maps.google" in href or "google.pt/maps" in href:
            continue
        if href.startswith("http"):
            return href
    return ""


def extract_course_url(stats_html: str) -> str:
    match = re.search(r"<a href='([^']+)' target=_blank class='btnAzul'>Página do curso na instituição</a>", stats_html, re.I)
    return match.group(1).strip() if match else ""


def extract_contact_block(details_html: str) -> str:
    match = re.search(r"Endere(?:ç|&ccedil;)o e Contactos da Institui(?:ç|&ccedil;)ão</h2>\s*(.*?)<h2>", details_html, re.S | re.I)
    return match.group(1) if match else ""


def parse_address_fields(details_html: str) -> dict[str, str]:
    block = extract_contact_block(details_html)
    if not block:
        return {"morada": "", "cidade": "", "distrito": ""}

    raw_parts = re.split(r"<br\s*/?>", block, flags=re.I)
    address_lines: list[str] = []
    for part in raw_parts:
        text = re.sub(r"<.*?>", " ", part)
        text = html_lib.unescape(text)
        text = clean_row_value(text)
        if not text:
            continue
        lower = text.casefold()
        if lower == "mapa" or lower.startswith("tel:") or lower.startswith("fax:") or "@" in text or text.startswith("http"):
            break
        address_lines.append(text)

    morada = ", ".join(address_lines)
    cidade = ""
    if address_lines:
        last = address_lines[-1]
        postal_match = re.search(r"\b\d{4}-\d{3}\s+(.+)$", last)
        cidade = postal_match.group(1).strip() if postal_match else last.strip()
        cidade = smart_city_case(cidade)

    return {"morada": morada, "cidade": cidade, "distrito": ""}


def build_lookup_tables(values: list[list[str]], idx: dict[str, int]):
    per_institution: dict[tuple[str, str], dict[str, collections.Counter[str]]] = {}
    city_to_district: dict[str, collections.Counter[str]] = {}

    for row in values[1:]:
        name = clean_row_value(row[idx["institution_name"]] if len(row) > idx["institution_name"] else "")
        code = clean_row_value(row[idx["institution_code"]] if len(row) > idx["institution_code"] else "")

        for key in (("name", name), ("code", code)):
            if not key[1]:
                continue
            bucket = per_institution.setdefault(key, {header: collections.Counter() for header in INSTITUTION_HEADERS})
            for header in INSTITUTION_HEADERS:
                value = clean_row_value(row[idx[header]] if len(row) > idx[header] else "")
                if value:
                    bucket[header][value] += 1

        city = clean_row_value(row[idx["cidade"]] if len(row) > idx["cidade"] else "")
        district = clean_row_value(row[idx["distrito"]] if len(row) > idx["distrito"] else "")
        if city and district:
            city_to_district.setdefault(normalize_key(city), collections.Counter())[district] += 1

    return per_institution, city_to_district


def best_counter_value(counter: collections.Counter[str]) -> str:
    return counter.most_common(1)[0][0] if counter else ""


def institution_known_value(
    per_institution: dict[tuple[str, str], dict[str, collections.Counter[str]]],
    institution_name: str,
    institution_code: str,
    header: str,
) -> str:
    for key in (("code", institution_code), ("name", institution_name)):
        bucket = per_institution.get(key)
        if bucket and bucket.get(header):
            value = best_counter_value(bucket[header])
            if value:
                return value
    return ""


def remember_institution_values(
    per_institution: dict[tuple[str, str], dict[str, collections.Counter[str]]],
    institution_name: str,
    institution_code: str,
    values: dict[str, str],
) -> None:
    for key in (("code", institution_code), ("name", institution_name)):
        if not key[1]:
            continue
        bucket = per_institution.setdefault(key, {header: collections.Counter() for header in INSTITUTION_HEADERS})
        for header in INSTITUTION_HEADERS:
            value = clean_row_value(values.get(header, ""))
            if value:
                bucket[header][value] += 1


def infer_district(city: str, city_to_district: dict[str, collections.Counter[str]]) -> str:
    if not city:
        return ""
    counter = city_to_district.get(normalize_key(city))
    return best_counter_value(counter) if counter else ""


def row_value(row: list[str], idx: dict[str, int], header: str) -> str:
    return clean_row_value(row[idx[header]] if len(row) > idx[header] else "")


def set_row_value(row: list[str], index: int, value: str) -> None:
    while len(row) <= index:
        row.append("")
    row[index] = value


def flush_columns(account: str, values: list[list[str]], idx: dict[str, int]) -> None:
    last_sheet_row = len(values)
    for header in TARGET_HEADERS:
        col = idx[header] + 1
        update_range(
            account,
            f"{TAB}!{column_letter(col)}2:{column_letter(col)}{last_sheet_row}",
            [[row[idx[header]] if len(row) > idx[header] else ""] for row in values[1:]],
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=os.environ.get("GOG_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--flush-every", type=int, default=80)
    parser.add_argument("--request-gap-low", type=float, default=0.25)
    parser.add_argument("--request-gap-high", type=float, default=0.9)
    parser.add_argument("--row-gap-low", type=float, default=0.0)
    parser.add_argument("--row-gap-high", type=float, default=0.15)
    args = parser.parse_args()

    ensure_dirs()
    cache = load_json(CACHE_PATH, {"details": {}, "course_url": {}, "institution_url": {}})
    official_cache = load_json(OFFICIAL_URLS_CACHE_PATH, {"institution_url": {}})
    values = get_sheet(args.account)
    headers = values[0]
    idx = {header: i for i, header in enumerate(headers)}

    required = [
        "updated_at",
        "course_code",
        "course_name",
        "institution_code",
        "institution_name",
        "estatisticas_do_curso",
        "detalhes_do_curso",
        "cidade",
        "distrito",
        "morada",
        "institution_url",
        "course_url",
    ]
    missing_headers = [header for header in required if header not in idx]
    if missing_headers:
        raise SystemExit(f"Missing required columns: {', '.join(missing_headers)}")

    per_institution, city_to_district = build_lookup_tables(values, idx)
    header_positions = {header: idx[header] + 1 for header in TARGET_HEADERS}
    log(f"live header mapping: {json.dumps(header_positions, ensure_ascii=False)}")

    candidates: list[tuple[int, list[str]]] = []
    for sheet_row, row in enumerate(values[1:], start=2):
        if any(not row_value(row, idx, header) for header in ["cidade", "distrito", "morada", "institution_url", "course_url"]):
            candidates.append((sheet_row, row))

    if args.limit:
        candidates = candidates[: args.limit]

    save_progress(
        {
            "status": "starting",
            "sheet_id": SHEET_ID,
            "tab": TAB,
            "header_positions": header_positions,
            "candidates": len(candidates),
            "processed": 0,
            "changed": 0,
            "errors": 0,
            "log_path": str(LOG_PATH.resolve()),
            "cache_path": str(CACHE_PATH.resolve()),
            "dryRun": args.dry_run,
            "startedAt": now_lisbon(),
        }
    )
    log(f"candidate rows: {len(candidates)}")

    processed = 0
    changed = 0
    errors = 0
    dirty = False

    for n, (sheet_row, row) in enumerate(candidates, start=1):
        course_code = row_value(row, idx, "course_code")
        course_name = row_value(row, idx, "course_name")
        institution_name = row_value(row, idx, "institution_name")
        institution_code = row_value(row, idx, "institution_code")
        details_url = row_value(row, idx, "detalhes_do_curso")
        stats_url = row_value(row, idx, "estatisticas_do_curso")

        log(f"[{n}/{len(candidates)}] row {sheet_row} :: {institution_code}/{course_code} :: {course_name} :: {institution_name}")
        try:
            row_changed = False
            details_payload = None

            for header in INSTITUTION_HEADERS:
                if row_value(row, idx, header):
                    continue

                value = institution_known_value(per_institution, institution_name, institution_code, header)

                if not value and header == "institution_url":
                    value = clean_row_value(cache.get("institution_url", {}).get(institution_code) or cache.get("institution_url", {}).get(institution_name) or official_cache.get("institution_url", {}).get(institution_name, ""))

                if not value and details_url:
                    details_key = details_url
                    details_payload = cache["details"].get(details_key)
                    if details_payload is None:
                        details_html = fetch(details_url)
                        parsed = parse_address_fields(details_html)
                        parsed["institution_url"] = extract_institution_url(details_html)
                        if not parsed["distrito"] and parsed["cidade"]:
                            parsed["distrito"] = infer_district(parsed["cidade"], city_to_district)
                        details_payload = parsed
                        cache["details"][details_key] = details_payload
                        if parsed.get("institution_url"):
                            cache.setdefault("institution_url", {})[institution_code or institution_name] = parsed["institution_url"]
                        save_json(CACHE_PATH, cache)
                        time.sleep(random.uniform(args.request_gap_low, args.request_gap_high))
                    value = clean_row_value(details_payload.get(header, ""))

                if value:
                    set_row_value(row, idx[header], value)
                    row_changed = True

            current_city = row_value(row, idx, "cidade")
            current_district = row_value(row, idx, "distrito")
            if current_city and not current_district:
                inferred = infer_district(current_city, city_to_district)
                if inferred:
                    set_row_value(row, idx["distrito"], inferred)
                    row_changed = True

            if not row_value(row, idx, "course_url") and stats_url:
                course_url = clean_row_value(cache["course_url"].get(stats_url, ""))
                if not course_url:
                    stats_html = fetch(stats_url)
                    course_url = extract_course_url(stats_html)
                    cache["course_url"][stats_url] = course_url
                    save_json(CACHE_PATH, cache)
                    time.sleep(random.uniform(args.request_gap_low, args.request_gap_high))
                if course_url:
                    set_row_value(row, idx["course_url"], course_url)
                    row_changed = True

            if row_changed:
                remember_institution_values(
                    per_institution,
                    institution_name,
                    institution_code,
                    {header: row_value(row, idx, header) for header in INSTITUTION_HEADERS},
                )
                city = row_value(row, idx, "cidade")
                district = row_value(row, idx, "distrito")
                if city and district:
                    city_to_district.setdefault(normalize_key(city), collections.Counter())[district] += 1
                set_row_value(row, idx["updated_at"], now_lisbon())
                changed += 1
                dirty = True
                log(
                    "row %s prepared :: cidade=%s distrito=%s morada=%s institution_url=%s course_url=%s"
                    % (
                        sheet_row,
                        bool(row_value(row, idx, "cidade")),
                        bool(row_value(row, idx, "distrito")),
                        bool(row_value(row, idx, "morada")),
                        bool(row_value(row, idx, "institution_url")),
                        bool(row_value(row, idx, "course_url")),
                    )
                )
            else:
                log(f"row {sheet_row} unchanged")

            processed += 1
        except Exception as exc:
            errors += 1
            log(f"row {sheet_row} error: {exc!r}")

        if not args.dry_run and dirty and processed % args.flush_every == 0:
            flush_columns(args.account, values, idx)
            dirty = False
            log(f"flushed target columns after {processed} processed rows")

        save_progress(
            {
                "status": "running",
                "sheet_id": SHEET_ID,
                "tab": TAB,
                "header_positions": header_positions,
                "candidates": len(candidates),
                "processed": processed,
                "changed": changed,
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

        if n < len(candidates):
            time.sleep(random.uniform(args.row_gap_low, args.row_gap_high))

    if not args.dry_run and dirty:
        flush_columns(args.account, values, idx)
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
            "changed": changed,
            "errors": errors,
            "remaining": len(candidates) - processed,
            "finishedAt": now_lisbon(),
            "log_path": str(LOG_PATH.resolve()),
            "cache_path": str(CACHE_PATH.resolve()),
            "dryRun": args.dry_run,
        }
    )
    log(f"done :: processed={processed} changed={changed} errors={errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
