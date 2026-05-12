#!/usr/bin/env python3
"""Fill missing course_description cells in the DGES course sheet.

Safety/behavior:
- maps sheet columns live by header name before writing
- writes ONLY the course_description column
- re-reads that column immediately before each flush and only fills cells still empty
- uses official sources: institution course page when usable, otherwise DGES course-detail metadata
- keeps log/progress/cache under projects/dges/data/
"""

from __future__ import annotations

import argparse
import datetime as dt
import html as html_lib
import json
import os
import random
import re
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SHEET_ID = "1m7LzrYoYTrCHYr3vBiaeK62ZOw-4GQVCbXse6d5FE6E"
TAB = "dges_cursos_2026"
DEFAULT_ACCOUNT = "tiago.carvalho@gmail.com"
DATA_DIR = Path("projects/dges/data")
LOG_PATH = DATA_DIR / "fill_missing_course_descriptions.log"
PROGRESS_PATH = DATA_DIR / "fill_missing_course_descriptions_progress.json"
CACHE_PATH = DATA_DIR / "fill_missing_course_descriptions_cache.json"
TARGET_HEADER = "course_description"
USER_AGENT = "Mozilla/5.0 (compatible; Nyx DGES course-description backfill/1.0; official-source condensation)"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def now_lisbon() -> str:
    return dt.datetime.now(ZoneInfo("Europe/Lisbon")).strftime("%Y-%m-%d %H:%M:%S %Z")


def log(msg: str) -> None:
    line = f"[{now_lisbon()}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def save_progress(payload: dict) -> None:
    payload = dict(payload)
    payload.setdefault("log_path", str(LOG_PATH.resolve()))
    payload.setdefault("cache_path", str(CACHE_PATH.resolve()))
    PROGRESS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sh(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def gog_base(account: str) -> list[str]:
    return ["gog", "sheets", "--account", account]


def get_sheet(account: str, range_a1: str = "A1:ZZ2000") -> list[list[str]]:
    return json.loads(sh(gog_base(account) + ["get", SHEET_ID, f"{TAB}!{range_a1}", "--json", "--no-input"]))["values"]


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


def clean(value: str) -> str:
    value = html_lib.unescape(value or "")
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip(" \t\n\r-–—|•")
    return value


def strip_tags(html: str) -> str:
    html = re.sub(r"<(?P<tag>script|style|noscript|svg|nav|footer|header)[^>]*>.*?</(?P=tag)>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<br\s*/?>", ". ", html, flags=re.I)
    html = re.sub(r"</(p|div|li|h[1-6]|td|tr)>", ". ", html, flags=re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return clean(html)


def strip_tags_plain(html: str) -> str:
    """Extract text without inserting sentence punctuation between table cells."""
    html = re.sub(r"<(?P<tag>script|style|noscript|svg|nav|footer|header)[^>]*>.*?</(?P=tag)>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    return clean(html)


def fetch(url: str, timeout: int) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.5"})

    # urllib's socket timeout does not reliably cover DNS/TLS stalls. Use a
    # process-level alarm too so one bad institutional site cannot freeze the
    # whole backfill; the DGES official fallback can then be tried.
    previous_handler = signal.getsignal(signal.SIGALRM)

    def raise_timeout(_signum, _frame):
        raise TimeoutError(f"fetch timeout after {timeout + 5}s: {url}")

    signal.signal(signal.SIGALRM, raise_timeout)
    signal.setitimer(signal.ITIMER_REAL, timeout + 5)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
            content_type = response.headers.get("content-type", "")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)

    if "pdf" in content_type.lower() or url.lower().endswith(".pdf"):
        raise ValueError("PDF source skipped")
    # Most DGES pages are ISO-8859-1; most institution pages are UTF-8. Try both safely.
    for enc in ("utf-8", "iso-8859-1", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            pass
    return data.decode("utf-8", "replace")


def meta_descriptions(html: str) -> list[str]:
    out: list[str] = []
    patterns = [
        r"<meta[^>]+(?:name|property)=[\"'](?:description|og:description|twitter:description)[\"'][^>]+content=[\"'](.*?)[\"']",
        r"<meta[^>]+content=[\"'](.*?)[\"'][^>]+(?:name|property)=[\"'](?:description|og:description|twitter:description)[\"']",
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, html, flags=re.S | re.I):
            value = clean(m.group(1))
            if value:
                out.append(value)
    return out


def score_text(text: str, course_name: str) -> int:
    lower = text.casefold()
    score = 0
    if course_name and any(tok.casefold() in lower for tok in re.findall(r"[A-Za-zÀ-ÿ]{5,}", course_name)[:4]):
        score += 4
    for word in ["curso", "licenciatura", "mestrado", "objetivo", "forma", "competências", "saídas profissionais", "perfil"]:
        if word in lower:
            score += 1
    if 120 <= len(text) <= 1800:
        score += 2
    if any(bad in lower for bad in ["cookie", "javascript", "menu", "newsletter", "404", "não encontrada", "not found"]):
        score -= 4
    return score


def first_sentences(text: str, max_chars: int = 760) -> str:
    text = clean(text)
    if len(text) <= max_chars:
        return text
    parts = re.split(r"(?<=[.!?])\s+", text)
    acc = ""
    for part in parts:
        if not part:
            continue
        candidate = (acc + " " + part).strip()
        if len(candidate) > max_chars:
            break
        acc = candidate
    return acc or text[:max_chars].rsplit(" ", 1)[0].strip()


def extract_institution_description(html: str, course_name: str) -> str:
    candidates: list[str] = []
    for meta in meta_descriptions(html):
        if len(meta) >= 90:
            candidates.append(meta)

    text = strip_tags(html)
    if not text:
        return ""

    # Prefer content around presentation/objective sections or around the course name.
    anchors = []
    for needle in [
        "Apresentação", "Apresentacao", "Objetivos", "Objectivos", "Caracterização", "Caracterizacao",
        "O Curso", "Sobre o Curso", "Competências", "Competencias", "Saídas Profissionais", "Saidas Profissionais",
        course_name,
    ]:
        if not needle:
            continue
        pos = text.casefold().find(needle.casefold())
        if pos >= 0:
            anchors.append(pos)

    for pos in sorted(set(anchors))[:8]:
        chunk = text[pos: pos + 1800]
        # Drop obvious navigation tails before condensing.
        chunk = re.split(r"\b(Plano de estudos|Unidades curriculares|Candidaturas|Contactos|Propinas|Condições de acesso)\b", chunk, maxsplit=1, flags=re.I)[0]
        chunk = first_sentences(chunk, 780)
        if len(chunk) >= 120:
            candidates.append(chunk)

    if not candidates:
        return ""
    best = max(candidates, key=lambda x: score_text(x, course_name))
    lower = best.casefold()
    # Reject administrative catalogue snippets; the DGES fallback is cleaner and still official.
    if any(bad in lower for bad in ["diploma conferido", "nível da qualificação", "suplemento ao diploma", "decreto-lei", "requisitos de acesso"]):
        return ""
    if not any(good in lower for good in ["visa", "pretende", "forma", "prepara", "permite", "objetivo", "competências", "saídas profissionais", "perfil"]):
        return ""
    if score_text(best, course_name) < 3:
        return ""
    return best


def dges_field(text: str, label: str, stop_labels: list[str]) -> str:
    pattern = re.escape(label) + r":?\s*(.*?)\s*(?=" + "|".join(re.escape(s) + r":?" for s in stop_labels) + r"|$)"
    m = re.search(pattern, text, flags=re.S | re.I)
    return clean(m.group(1)) if m else ""


def parse_dges_description(html: str, course_name: str, institution_name: str) -> str:
    text = strip_tags_plain(html)
    area = dges_field(text, "Área CNAEF", ["Duração", "ECTS", "Tipo de Ensino", "Concurso"])
    duration = dges_field(text, "Duração", ["ECTS", "Tipo de Ensino", "Concurso"])
    ects = dges_field(text, "ECTS", ["Tipo de Ensino", "Concurso", "Vagas"])
    ensino = dges_field(text, "Tipo de Ensino", ["Concurso", "Vagas", "Provas de Ingresso"])
    vagas = dges_field(text, "Vagas para 2026-2027", ["Pré-Requisitos", "Provas de Ingresso", "Classificações Mínimas"])
    area_label = re.sub(r"^\d+\s+", "", area).strip()

    bits = [f"Curso superior em **{course_name}**"]
    if institution_name:
        bits.append(f"lecionado por {institution_name}")
    if area_label:
        bits.append(f"na área **{area_label}**")
    sentence = ", ".join(bits) + "."

    details = []
    if duration and ects:
        details.append(f"tem duração de {duration.lower()} e {ects} ECTS")
    elif duration:
        details.append(f"tem duração de {duration.lower()}")
    elif ects:
        details.append(f"tem {ects} ECTS")
    if ensino:
        details.append(f"integra o {ensino.lower()}")
    if vagas:
        details.append(f"dispõe de {vagas} vagas para 2026-2027")

    if details:
        sentence += " Segundo a ficha oficial DGES, " + ", ".join(details).strip() + "."
    sentence += " Apresenta uma visão rápida da oferta formativa, enquadramento oficial e condições-base do curso."
    desc = clean(sentence)
    return desc if len(desc) >= 100 else ""


def normalize_description(desc: str, course_name: str) -> str:
    desc = clean(desc)
    if len(desc) > 2000:
        desc = first_sentences(desc, 1950)
    return desc


def row_value(row: list[str], idx: dict[str, int], header: str) -> str:
    i = idx[header]
    return clean(row[i] if len(row) > i else "")


def build_description(row: list[str], idx: dict[str, int], cache: dict, timeout: int) -> tuple[str, str]:
    course_name = row_value(row, idx, "course_name")
    institution_name = row_value(row, idx, "institution_name")
    course_url = row_value(row, idx, "course_url")
    details_url = row_value(row, idx, "detalhes_do_curso")
    cache_key = f"{row_value(row, idx, 'institution_code')}::{row_value(row, idx, 'course_code')}"

    cached = cache.get("descriptions", {}).get(cache_key)
    if cached is not None:
        return cached.get("description", ""), cached.get("source", "cache")

    source = ""
    desc = ""
    errors: list[str] = []

    # Prefer DGES detail pages for this backfill. They are official, compact and
    # predictable; some institutional pages are huge SPA/catalogue pages that can
    # burn minutes in parsing. Use the institutional page only as fallback.
    if details_url:
        try:
            html = fetch(details_url, timeout=timeout)
            desc = parse_dges_description(html, course_name, institution_name)
            if desc:
                source = details_url
        except Exception as exc:
            errors.append(f"dges_detail={type(exc).__name__}:{exc}")

    if not desc and course_url and course_url.lower().startswith(("http://", "https://")):
        try:
            html = fetch(course_url, timeout=timeout)
            desc = extract_institution_description(html, course_name)
            if desc:
                source = course_url
        except Exception as exc:
            errors.append(f"institution_page={type(exc).__name__}:{exc}")

    desc = normalize_description(desc, course_name) if desc else ""
    cache.setdefault("descriptions", {})[cache_key] = {"description": desc, "source": source, "errors": errors, "updatedAt": now_lisbon()}
    return desc, source


def contiguous_groups(pending: dict[int, str]) -> list[tuple[int, int, list[list[str]]]]:
    groups = []
    current_start = None
    current_values: list[list[str]] = []
    last_row = None
    for sheet_row in sorted(pending):
        if current_start is None or last_row is None or sheet_row != last_row + 1:
            if current_start is not None and last_row is not None:
                groups.append((current_start, last_row, current_values))
            current_start = sheet_row
            current_values = []
        current_values.append([pending[sheet_row]])
        last_row = sheet_row
    if current_start is not None and last_row is not None:
        groups.append((current_start, last_row, current_values))
    return groups


def flush_pending(account: str, desc_col_letter: str, pending: dict[int, str], counters: dict, dry_run: bool) -> None:
    if not pending:
        return
    latest = get_sheet(account, f"{desc_col_letter}1:{desc_col_letter}2000")
    still_empty: dict[int, str] = {}
    for sheet_row, desc in pending.items():
        current = ""
        idx0 = sheet_row - 1
        if idx0 < len(latest) and latest[idx0]:
            current = clean(latest[idx0][0])
        if current:
            counters["skipped_already_filled"] += 1
            log(f"row {sheet_row} skipped at flush: course_description already filled")
        else:
            still_empty[sheet_row] = desc

    for start, end, values in contiguous_groups(still_empty):
        rng = f"{TAB}!{desc_col_letter}{start}:{desc_col_letter}{end}"
        if dry_run:
            log(f"dry-run would update {rng} ({len(values)} rows)")
        else:
            update_range(account, rng, values)
            log(f"updated {rng} ({len(values)} rows)")
        counters["written"] += len(values)
    pending.clear()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--account", default=os.environ.get("GOG_ACCOUNT", DEFAULT_ACCOUNT))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--flush-every", type=int, default=40)
    parser.add_argument("--timeout", type=int, default=14)
    parser.add_argument("--request-gap-low", type=float, default=0.35)
    parser.add_argument("--request-gap-high", type=float, default=1.2)
    parser.add_argument("--row-gap-low", type=float, default=0.05)
    parser.add_argument("--row-gap-high", type=float, default=0.25)
    args = parser.parse_args()

    ensure_dirs()
    cache = load_json(CACHE_PATH, {"descriptions": {}})
    values = get_sheet(args.account)
    headers = values[0]
    idx = {header: i for i, header in enumerate(headers)}
    required = [
        "course_code", "course_name", "institution_code", "institution_name",
        "detalhes_do_curso", "course_url", TARGET_HEADER,
    ]
    missing = [h for h in required if h not in idx]
    if missing:
        raise SystemExit(f"Missing required columns: {', '.join(missing)}")

    desc_col = idx[TARGET_HEADER] + 1
    desc_col_letter = column_letter(desc_col)
    candidates = []
    for sheet_row, row in enumerate(values[1:], start=2):
        if not row_value(row, idx, TARGET_HEADER):
            candidates.append((sheet_row, row))
    if args.limit:
        candidates = candidates[: args.limit]

    counters = {
        "processed": 0,
        "prepared": 0,
        "written": 0,
        "no_data": 0,
        "errors": 0,
        "skipped_already_filled": 0,
    }
    pending: dict[int, str] = {}
    header_positions = {TARGET_HEADER: desc_col}
    log(f"starting course_description backfill :: candidates={len(candidates)} :: target={desc_col_letter} :: dry_run={args.dry_run}")
    save_progress({
        "status": "starting", "sheet_id": SHEET_ID, "tab": TAB, "header_positions": header_positions,
        "candidates": len(candidates), **counters, "startedAt": now_lisbon(), "dryRun": args.dry_run,
    })

    for n, (sheet_row, row) in enumerate(candidates, start=1):
        course_code = row_value(row, idx, "course_code")
        course_name = row_value(row, idx, "course_name")
        institution_name = row_value(row, idx, "institution_name")
        log(f"[{n}/{len(candidates)}] row {sheet_row} :: {course_code} :: {course_name} :: {institution_name}")
        try:
            desc, source = build_description(row, idx, cache, args.timeout)
            counters["processed"] += 1
            if desc:
                pending[sheet_row] = desc
                counters["prepared"] += 1
                log(f"row {sheet_row} prepared ({len(desc)} chars) :: source={source}")
            else:
                counters["no_data"] += 1
                log(f"row {sheet_row} left empty: no reliable official description")
        except Exception as exc:
            counters["processed"] += 1
            counters["errors"] += 1
            log(f"row {sheet_row} error: {exc!r}")

        if n % 10 == 0:
            save_json(CACHE_PATH, cache)
        if len(pending) >= args.flush_every:
            flush_pending(args.account, desc_col_letter, pending, counters, args.dry_run)
            save_json(CACHE_PATH, cache)

        save_progress({
            "status": "running", "sheet_id": SHEET_ID, "tab": TAB, "header_positions": header_positions,
            "candidates": len(candidates), "remaining": len(candidates) - n,
            "lastRow": sheet_row, "lastCourseCode": course_code, "lastCourseName": course_name,
            "lastInstitutionName": institution_name, **counters, "updatedAt": now_lisbon(), "dryRun": args.dry_run,
        })
        if n < len(candidates):
            time.sleep(random.uniform(args.row_gap_low, args.row_gap_high))
            # Spread official-source requests a little; cache hits make this cheap.
            time.sleep(random.uniform(args.request_gap_low, args.request_gap_high))

    flush_pending(args.account, desc_col_letter, pending, counters, args.dry_run)
    save_json(CACHE_PATH, cache)
    save_progress({
        "status": "completed-dry-run" if args.dry_run else "completed", "sheet_id": SHEET_ID, "tab": TAB,
        "header_positions": header_positions, "candidates": len(candidates), "remaining": 0,
        **counters, "finishedAt": now_lisbon(), "dryRun": args.dry_run,
    })
    log("done :: " + " ".join(f"{k}={v}" for k, v in counters.items()))
    return 0 if counters["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
